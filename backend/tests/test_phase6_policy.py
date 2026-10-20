"""Phase6 regressions against real disposable PostgreSQL; HTTP outcomes are controlled."""

import os
import uuid
from datetime import timedelta

import pytest
from sqlalchemy import select
from test_database import api_client, sample
from test_database import database as database
from test_notifications import Delivery, Event, drain, records, setup

from app.analytics import aggregate
from app.db import Session
from app.incidents import close_incident
from app.models import CheckResult, Monitor, now
from app.notifications import refresh_down_eligibility

pytestmark = pytest.mark.skipif(not os.environ.get("TEST_DATABASE_URL"), reason="Disposable DB")


@pytest.mark.parametrize(
    "mutation,expected",
    [
        ("none", ["DOWN", "RECOVERY"]),
        ("extend-before", []),
        ("extend-after", ["DOWN", "RECOVERY"]),
        ("delete-before", ["DOWN", "RECOVERY"]),
        ("delete-after-recovery", []),
    ],
)
async def test_dispatcher_offline_maintenance_deadlines_and_edits(monkeypatch, mutation, expected):
    start = timestamp = now() + timedelta(days=1)
    for module in ("notifications", "maintenance", "worker"):
        monkeypatch.setattr(f"app.{module}.now", lambda: timestamp)
    sent = []

    async def sender(payload):
        sent.append(payload["event_type"])

    async with api_client() as api:
        m, _ = await setup(api)
        payload = {
            "name": "policy window",
            "monitor_id": m["id"],
            "start_at": (start - timedelta(seconds=1)).isoformat(),
            "end_at": (start + timedelta(seconds=10)).isoformat(),
        }
        response = await api.post("/api/maintenance", json=payload)
        assert response.status_code == 201, response.text
        window = response.json()
        await sample(api, m["id"], monkeypatch)
        down = (await records())[0]
        assert down.down_eligible_at == start + timedelta(seconds=10)
        assert not down.down_required
        # No reconciliation/dispatch from confirmation until after recovery.
        if mutation.startswith("extend"):
            timestamp = start + timedelta(seconds=5 if mutation == "extend-before" else 15)
            response = await api.put(
                f"/api/maintenance/{window['id']}",
                json={
                    **payload,
                    "end_at": (start + timedelta(seconds=30)).isoformat(),
                    "config_version": 1,
                },
            )
            assert response.status_code == 200, response.text
        elif mutation == "delete-before":
            timestamp = start + timedelta(seconds=5)
            assert (
                await api.delete(f"/api/maintenance/{window['id']}?config_version=1")
            ).status_code == 204
        timestamp = start + timedelta(seconds=5 if mutation == "delete-after-recovery" else 20)
        await sample(api, m["id"], monkeypatch, True)
        if mutation == "delete-after-recovery":
            assert (
                await api.delete(f"/api/maintenance/{window['id']}?config_version=1")
            ).status_code == 204
        timestamp = start + timedelta(seconds=40)
        for _ in range(3):
            await drain(sender)
            timestamp += timedelta(seconds=3)
        assert sent == expected
        rows = await records()
        assert len(rows) == 2
        assert {r.status for r in rows} == ({"SENT"} if expected else {"CANCELLED"})


async def test_quick_recovery_shared_recipient_and_definite_retry(monkeypatch):
    timestamp = now()
    monkeypatch.setattr("app.notifications.now", lambda: timestamp)
    calls = []

    async def sender(payload):
        calls.append((payload["delivery_id"], payload["event_type"]))
        if len(calls) == 1:
            raise ConnectionRefusedError("controlled SMTP refusal")

    async with api_client() as api:
        m, _ = await setup(api)
        response = await api.post(
            "/api/groups",
            json={
                "name": "Shared",
                "monitor_ids": [m["id"]],
                "recipients": ["OPS@example.com"],
            },
        )
        assert response.status_code == 201
        await sample(api, m["id"], monkeypatch)
        await drain(sender)
        await sample(api, m["id"], monkeypatch, True)
        for _ in range(3):
            timestamp += timedelta(seconds=10)
            await drain(sender)
        assert [kind for _, kind in calls] == ["DOWN", "DOWN", "RECOVERY"]
        assert calls[0][0] == calls[1][0]  # Same persisted identity across retry.
        assert len(await records()) == 2
        async with Session() as db:
            assert len((await db.scalars(select(Event))).all()) == 2
            assert all(r.status == "SENT" for r in (await db.scalars(select(Delivery))).all())


async def test_manual_bursts_equal_timestamps_and_window_edge_never_double_coverage():
    end = now()
    start = end - timedelta(days=1)
    async with api_client() as api:
        m, _ = await setup(api)
        mid = uuid.UUID(m["id"])
        async with Session() as db, db.begin():
            for offset, cadence in [
                (0, 30),
                (0, 30),
                (10, 30),
                (20, 30),
                (50, None),
                (300, 60),
                (86400, 30),
            ]:
                db.add(
                    CheckResult(
                        monitor_id=mid,
                        checked_at=start + timedelta(seconds=offset),
                        success=True,
                        response_ms=10,
                        config_version=1,
                        interval_seconds=cadence,
                    )
                )
        async with Session() as db:
            data = await aggregate(db, mid, "24h", end)
        # [0,50) union and [300,360); exact end sample excluded, legacy makes no span.
        assert data["samples"] == 6
        assert data["uptime_percent"] == 100
        assert data["unobserved_seconds"] == 86400 - 110
        assert data["buckets"][0]["coverage_percent"] == pytest.approx(50 / 300 * 100)
        assert data["buckets"][1]["coverage_percent"] == 20


async def test_recovery_observed_inside_window_before_persistence_delay(monkeypatch):
    start = timestamp = now() + timedelta(days=1)
    for module in ("notifications", "worker"):
        monkeypatch.setattr(f"app.{module}.now", lambda: timestamp)
    async with api_client() as api:
        m, _ = await setup(api)
        response = await api.post(
            "/api/maintenance",
            json={
                "name": "boundary",
                "monitor_id": m["id"],
                "start_at": start.isoformat(),
                "end_at": (start + timedelta(seconds=10)).isoformat(),
            },
        )
        assert response.status_code == 201
        await sample(api, m["id"], monkeypatch)
        timestamp = start + timedelta(seconds=20)
        async with Session() as db, db.begin():
            await refresh_down_eligibility(db, {uuid.UUID(m["id"])})
        assert (await records())[0].down_required
        # Successful HTTP completed at +5, before waiting to persist its recovery.
        async with Session() as db, db.begin():
            monitor = await db.scalar(
                select(Monitor).where(Monitor.id == uuid.UUID(m["id"])).with_for_update()
            )
            await close_incident(db, monitor.id, "RECOVERED", start + timedelta(seconds=5))
        assert not (await records())[0].down_required
        sent = []

        async def sender(payload):
            sent.append(payload)

        for _ in range(3):
            await drain(sender)
            timestamp += timedelta(seconds=3)
        assert not sent and {r.status for r in await records()} == {"CANCELLED"}


@pytest.mark.parametrize("recovered,down_sent", [(False, False), (True, False), (True, True)])
async def test_route_revocation_while_dispatcher_offline_is_terminal(
    monkeypatch, recovered, down_sent
):
    sent = []

    async def sender(payload):
        sent.append(payload["event_type"])

    async with api_client() as api:
        m, group = await setup(api)
        await sample(api, m["id"], monkeypatch)
        if down_sent:
            await drain(sender)
        if recovered:
            await sample(api, m["id"], monkeypatch, True)
        payload = {
            "name": group["name"],
            "monitor_ids": [m["id"]],
            "recipients": [],
            "config_version": 1,
        }
        assert (await api.put(f"/api/groups/{group['id']}", json=payload)).status_code == 200
        assert {r.status for r in await records()} == (
            {"SENT", "CANCELLED"} if down_sent else {"CANCELLED"}
        )
        payload.update(config_version=2, recipients=group["recipients"])
        assert (await api.put(f"/api/groups/{group['id']}", json=payload)).status_code == 200
        if not recovered:
            await sample(api, m["id"], monkeypatch, True)
        await drain(sender)
        assert sent == (["DOWN"] if down_sent else [])
        assert {r.status for r in await records()} == (
            {"SENT", "CANCELLED"} if down_sent else {"CANCELLED"}
        )
