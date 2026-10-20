import asyncio
import os
import smtplib
import uuid
from datetime import timedelta

import httpx
import pytest
from sqlalchemy import func, select, text
from sqlalchemy.exc import DBAPIError, IntegrityError
from test_database import api_client, create, edit_payload, sample
from test_database import database as database

from app.db import Session, engine
from app.dispatcher import classify_error, dispatch_one
from app.models import (
    Incident,
    now,
)
from app.models import (
    NotificationDelivery as Delivery,
)
from app.models import (
    NotificationEvent as Event,
)
from app.models import (
    NotificationRoute as Route,
)
from app.notifications import acknowledge, claim_deliveries, prepare, reconcile

pytestmark = pytest.mark.skipif(
    not os.environ.get("TEST_DATABASE_URL"), reason="Disposable DB required"
)


async def setup(api, recipients=None):
    m = await create(api, failure_threshold=1)
    g = (
        await api.post(
            "/api/groups",
            json={
                "name": "Ops",
                "monitor_ids": [m["id"]],
                "recipients": recipients or ["ops@example.com"],
            },
        )
    ).json()
    return m, g


def window(**changes):
    timestamp = now()
    return {
        "name": "planned",
        "start_at": (timestamp - timedelta(minutes=1)).isoformat(),
        "end_at": (timestamp + timedelta(hours=1)).isoformat(),
        **changes,
    }


async def records():
    async with Session() as db:
        return (await db.scalars(select(Delivery).order_by(Delivery.created_at))).all()


async def drain(sender):
    for row in await claim_deliveries(100):
        await dispatch_one(row, sender)


async def test_default_threshold_transient_failure_and_logical_email_pair(monkeypatch):
    sent = []

    async def sender(payload):
        sent.append(payload)

    async with api_client() as api:
        m = await create(api)
        assert m["failure_threshold"] == 2
        response = await api.post(
            "/api/groups",
            json={"name": "Ops", "monitor_ids": [m["id"]], "recipients": ["ops@example.com"]},
        )
        assert response.status_code == 201
        await sample(api, m["id"], monkeypatch, True)
        await sample(api, m["id"], monkeypatch)
        await drain(sender)
        assert (await api.get(f"/api/monitors/{m['id']}")).json()["state"] == "UP"
        assert (await api.get("/api/incidents")).json()["items"] == []
        async with Session() as db:
            for model in (Event, Route, Delivery):
                assert await db.scalar(select(func.count()).select_from(model)) == 0
        assert sent == []
        # A success resets the streak; the next isolated failure is still transient.
        await sample(api, m["id"], monkeypatch, True)
        await sample(api, m["id"], monkeypatch)
        await drain(sender)
        assert not sent and not await records()
        await sample(api, m["id"], monkeypatch)
        await drain(sender)
        assert [p["event_type"] for p in sent] == ["DOWN"]
        for _ in range(3):
            await sample(api, m["id"], monkeypatch)
            await drain(sender)
        assert len(sent) == 1
        await sample(api, m["id"], monkeypatch, True)
        await drain(sender)
        await sample(api, m["id"], monkeypatch, True)
        await drain(sender)
        assert [p["event_type"] for p in sent] == ["DOWN", "RECOVERY"]
        assert sent[0]["incident_id"] == sent[1]["incident_id"]
        assert len(await records()) == 2


async def test_permanent_smtp_rejection_is_terminal_without_false_recovery(monkeypatch):
    calls = []

    async def rejected(payload):
        calls.append(payload)
        raise smtplib.SMTPDataError(550, b"recipient unavailable")

    async with api_client() as api:
        m, _ = await setup(api)
        await sample(api, m["id"], monkeypatch)
        await drain(rejected)
        down = (await records())[0]
        assert down.status == "FAILED" and down.attempts == 1
        assert down.last_error == "smtp_permanent" and down.send_started_at is None
        await reconcile()
        await drain(rejected)
        await sample(api, m["id"], monkeypatch, True)
        await drain(rejected)
        assert len(calls) == 1
        assert {r.status for r in await records()} == {"FAILED", "CANCELLED"}


async def test_maintenance_crud_timezone_conflicts_and_target_cascade():
    async with api_client() as api:
        m, g = await setup(api)
        payload = window(monitor_id=m["id"])
        response = await api.post("/api/maintenance", json=payload)
        assert response.status_code == 201
        w = response.json()
        assert w["state"] == "ACTIVE"
        page = (await api.get("/api/maintenance?state=ACTIVE")).json()
        assert page["active_monitor_ids"] == [m["id"]]
        updated = await api.put(
            f"/api/maintenance/{w['id']}",
            json={
                **payload,
                "monitor_id": None,
                "group_id": g["id"],
                "config_version": 1,
                "name": "Group work",
            },
        )
        assert updated.status_code == 200 and updated.json()["config_version"] == 2
        assert (
            await api.put(f"/api/maintenance/{w['id']}", json={**payload, "config_version": 1})
        ).status_code == 409
        assert (await api.delete(f"/api/maintenance/{w['id']}?config_version=1")).status_code == 409
        assert (await api.delete(f"/api/maintenance/{w['id']}?config_version=2")).status_code == 204
        assert (
            await api.post("/api/maintenance", json=window(group_id=g["id"]))
        ).status_code == 201
        await api.delete(f"/api/groups/{g['id']}?config_version=1")
        assert (await api.get("/api/maintenance")).json()["items"] == []
        assert (
            await api.post("/api/maintenance", json=window(monitor_id=m["id"]))
        ).status_code == 201
        await api.delete(f"/api/monitors/{m['id']}")
        assert (await api.get("/api/maintenance")).json()["items"] == []


@pytest.mark.parametrize(
    "bad",
    [
        {},
        {"monitor_id": str(uuid.uuid4()), "group_id": str(uuid.uuid4())},
        {"start_at": "2026-10-19T10:00:00"},
        {"end_at": "2000-01-01T00:00:00Z"},
        {"name": "  "},
    ],
)
async def test_window_validation(bad):
    async with api_client() as api:
        m = await create(api)
        payload = window(monitor_id=m["id"])
        if not bad:
            payload.pop("monitor_id")
        else:
            payload.update(bad)
        assert (await api.post("/api/maintenance", json=payload)).status_code == 422


async def test_overlapping_windows_exact_boundaries_and_reconcile_without_result(monkeypatch):
    timestamp = now()
    monkeypatch.setattr("app.notifications.now", lambda: timestamp)
    monkeypatch.setattr("app.maintenance.now", lambda: timestamp)
    sent = []

    async def sender(p):
        sent.append(p)

    async with api_client() as api:
        m, g = await setup(api)
        # First window starts inclusively at timestamp, second extends the union.
        for end in (10, 20):
            assert (
                await api.post(
                    "/api/maintenance",
                    json=window(
                        group_id=g["id"],
                        start_at=timestamp.isoformat(),
                        end_at=(timestamp + timedelta(seconds=end)).isoformat(),
                    ),
                )
            ).status_code == 201
        await sample(api, m["id"], monkeypatch)
        before = (await api.get(f"/api/monitors/{m['id']}/results")).json()
        assert (await api.get(f"/api/monitors/{m['id']}")).json()["state"] == "DOWN"
        await drain(sender)
        assert not sent and (await records())[0].attempts == 0
        timestamp += timedelta(seconds=10)
        await reconcile()
        await drain(sender)
        assert not sent
        timestamp += timedelta(seconds=10)
        await reconcile()
        await drain(sender)
        assert len(sent) == 1 and sent[0]["event_type"] == "DOWN"
        assert (await api.get(f"/api/monitors/{m['id']}/results")).json() == before
        await sample(api, m["id"], monkeypatch)
        await drain(sender)
        assert len(sent) == 1


async def test_shared_address_independent_group_routes_and_frozen_recipients(monkeypatch):
    sent = []

    async def sender(p):
        sent.append(p)

    async with api_client() as api:
        m, g = await setup(api, ["Shared@example.com", "only-a@example.com"])
        other = (
            await api.post(
                "/api/groups",
                json={
                    "name": "B",
                    "monitor_ids": [m["id"]],
                    "recipients": ["shared@example.com", "only-b@example.com"],
                },
            )
        ).json()
        await api.post("/api/maintenance", json=window(group_id=g["id"]))
        await sample(api, m["id"], monkeypatch)
        await drain(sender)
        assert {p["email"] for p in sent} == {"shared@example.com", "only-b@example.com"}
        # New recipient never receives this old event; removing A's old route revokes it.
        await api.put(
            f"/api/groups/{g['id']}",
            json={
                "name": "A",
                "monitor_ids": [m["id"]],
                "recipients": ["new@example.com"],
                "config_version": 1,
            },
        )
        async with Session() as db, db.begin():
            for row in (
                await db.scalars(select(Delivery).where(Delivery.status == "PENDING"))
            ).all():
                row.next_attempt_at = now() - timedelta(seconds=1)
        await reconcile()
        await drain(sender)
        assert len(sent) == 2 and {r.status for r in await records()} == {"SENT", "CANCELLED"}
        assert (await api.get(f"/api/groups/{other['id']}")).status_code == 200


@pytest.mark.parametrize("down_sent", [False, True])
async def test_recovery_in_maintenance_keeps_only_required_recovery(monkeypatch, down_sent):
    timestamp = now()
    monkeypatch.setattr("app.notifications.now", lambda: timestamp)
    sent = []

    async def sender(p):
        sent.append(p)

    async with api_client() as api:
        m, g = await setup(api)
        if not down_sent:
            await api.post("/api/maintenance", json=window(monitor_id=m["id"]))
        await sample(api, m["id"], monkeypatch)
        await drain(sender)
        if down_sent:
            await api.post("/api/maintenance", json=window(group_id=g["id"]))
        await sample(api, m["id"], monkeypatch, True)
        await drain(sender)
        assert len(sent) == int(down_sent)
        timestamp += timedelta(hours=2)
        await reconcile()
        await drain(sender)
        assert [p["event_type"] for p in sent] == (["DOWN", "RECOVERY"] if down_sent else [])


@pytest.mark.parametrize("operation", ["pause", "edit", "delete", "remove-group", "remove-member"])
async def test_pending_down_revoked_by_administrative_changes(monkeypatch, operation):
    async with api_client() as api:
        m, g = await setup(api)
        await sample(api, m["id"], monkeypatch)
        claimed = (await claim_deliveries())[0]
        if operation == "pause":
            await api.post(f"/api/monitors/{m['id']}/pause", json={"config_version": 1})
        elif operation == "edit":
            await api.put(f"/api/monitors/{m['id']}", json=edit_payload(m, name="Edited"))
        elif operation == "delete":
            await api.delete(f"/api/monitors/{m['id']}")
        elif operation == "remove-group":
            await api.delete(f"/api/groups/{g['id']}?config_version=1")
        else:
            await api.put(
                f"/api/groups/{g['id']}",
                json={
                    "name": "A",
                    "monitor_ids": [],
                    "recipients": g["recipients"],
                    "config_version": 1,
                },
            )
        assert await prepare(claimed) is None
        assert all(r.status == "CANCELLED" for r in await records())
        async with Session() as db:
            assert not await db.scalar(select(Event.id).where(Event.event_type == "RECOVERY"))


async def test_two_dispatchers_expiry_and_stale_ack(monkeypatch):
    async with api_client() as api:
        m, _ = await setup(api)
        await sample(api, m["id"], monkeypatch)
        first, second = await asyncio.gather(claim_deliveries(), claim_deliveries())
        assert len(first + second) == 1
        old = (first + second)[0]
        assert await prepare(old)
        async with Session() as db, db.begin():
            row = await db.get(Delivery, old.id)
            row.lease_until = now() - timedelta(seconds=1)
        fresh = (await claim_deliveries())[0]
        assert await prepare(old) is None
        await acknowledge(old)
        assert (await records())[0].status == "INFLIGHT"
        assert await prepare(fresh)
        await acknowledge(fresh)
        assert (await records())[0].status == "SENT"


async def test_recovered_before_down_send_preserves_required_pair(monkeypatch):
    async with api_client() as api:
        m, _ = await setup(api)
        await sample(api, m["id"], monkeypatch)
        await sample(api, m["id"], monkeypatch, True)
        sent = []

        async def sender(p):
            sent.append(p)

        await drain(sender)
        await reconcile()
        await drain(sender)
        assert [p["event_type"] for p in sent] == ["DOWN", "RECOVERY"]
        assert all(r.status == "SENT" for r in await records())


async def test_inflight_down_ack_after_recovery_preserves_order(monkeypatch):
    async with api_client() as api:
        m, _ = await setup(api)
        await sample(api, m["id"], monkeypatch)
        claimed = (await claim_deliveries())[0]
        assert await prepare(claimed)
        await sample(api, m["id"], monkeypatch, True)
        recovery = (await claim_deliveries())[0]
        assert await prepare(recovery) is None
        await acknowledge(claimed)
        async with Session() as db, db.begin():
            row = await db.get(Delivery, recovery.id)
            row.next_attempt_at = now()
        assert (await prepare((await claim_deliveries())[0]))["event_type"] == "RECOVERY"


@pytest.mark.parametrize(
    "error,category,permanent,definite",
    [
        (ConnectionRefusedError(), "smtp_network", False, True),
        (TimeoutError(), "smtp_timeout", False, False),
        (smtplib.SMTPDataError(450, b"temporary"), "smtp_temporary", False, True),
        (smtplib.SMTPDataError(550, b"permanent"), "smtp_permanent", True, True),
        (
            smtplib.SMTPRecipientsRefused({"x@example.com": (550, b"no")}),
            "smtp_permanent",
            True,
            True,
        ),
        (smtplib.SMTPServerDisconnected(), "smtp_network", False, False),
        (ValueError(), "invalid_message", True, True),
    ],
)
def test_smtp_error_classification(error, category, permanent, definite):
    assert classify_error(error) == (category, permanent, definite)


async def test_retry_backoff_limit_and_definite_rejection(monkeypatch):
    timestamp = now()
    monkeypatch.setattr("app.notifications.now", lambda: timestamp)

    async def refused(p):
        raise smtplib.SMTPDataError(450, b"temporary")

    async with api_client() as api:
        m, _ = await setup(api)
        await sample(api, m["id"], monkeypatch)
        for attempt in range(1, 9):
            await drain(refused)
            row = (await records())[0]
            assert row.attempts == attempt and row.send_started_at is None
            assert (row.next_attempt_at - timestamp).total_seconds() == min(
                300, 5 * 2 ** (attempt - 1)
            )
            assert await claim_deliveries() == []
            timestamp = row.next_attempt_at
        assert (await records())[0].status == "FAILED"


async def test_event_constraints_and_atomic_rollback(monkeypatch):
    from app.notifications import create_event

    async def fail(db, *args):
        await create_event(db, *args)
        await db.flush()
        await db.execute(text("SELECT 1/0"))

    async with api_client() as api:
        m, _ = await setup(api)
        monkeypatch.setattr("app.incidents.create_event", fail)
        with pytest.raises(DBAPIError):
            await sample(api, m["id"], monkeypatch)
        async with Session() as db:
            for model in (Incident, Event, Route, Delivery):
                assert await db.scalar(select(func.count()).select_from(model)) == 0
        monkeypatch.setattr("app.incidents.create_event", create_event)
        async with Session() as db, db.begin():
            from app.models import Monitor

            row = await db.get(Monitor, uuid.UUID(m["id"]))
            row.lease_until = now() - timedelta(seconds=1)
        from app.worker import claim_due, execute

        await execute((await claim_due(1))[0], None)
        async with Session() as db:
            event = await db.scalar(select(Event))
        with pytest.raises(IntegrityError):
            async with Session() as db, db.begin():
                db.add(
                    Event(
                        incident_id=event.incident_id, event_type="DOWN", monitor_name="duplicate"
                    )
                )
        delivery = (await records())[0]
        with pytest.raises(IntegrityError):
            async with Session() as db, db.begin():
                db.add(Delivery(event_id=delivery.event_id, email=delivery.email))


async def test_actual_smtp_acceptance_and_real_mailpit_api(monkeypatch):
    assert os.environ.get("MAILPIT_URL"), "Compose/CI must supply the real Mailpit catcher"
    marker = "smtp-" + uuid.uuid4().hex
    async with api_client() as api:
        m, _ = await setup(api, [marker + "@example.com"])
        await sample(api, m["id"], monkeypatch)
        for row in await claim_deliveries():
            await dispatch_one(row)
        assert (await records())[0].status == "SENT"
        async with httpx.AsyncClient(base_url=os.environ["MAILPIT_URL"]) as mail:
            messages = (await mail.get("/api/v1/messages", params={"limit": 100})).json()[
                "messages"
            ]
            matches = [
                v for v in messages if any(t["Address"] == marker + "@example.com" for t in v["To"])
            ]
            assert len(matches) == 1 and "DOWN" in matches[0]["Subject"]
            message = (await mail.get("/api/v1/message/" + matches[0]["ID"])).json()
            assert str((await records())[0].id) in message["MessageID"]
            assert "Incident:" in message["Text"]
    await engine.dispose()


async def test_monitor_window_blocks_all_groups_and_claim_rechecks_policy(monkeypatch):
    timestamp = now()
    monkeypatch.setattr("app.notifications.now", lambda: timestamp)
    async with api_client() as api:
        m, _ = await setup(api)
        await api.post(
            "/api/groups",
            json={"name": "B", "monitor_ids": [m["id"]], "recipients": ["other@example.com"]},
        )
        await sample(api, m["id"], monkeypatch)
        claims = await claim_deliveries()
        response = await api.post("/api/maintenance", json=window(monitor_id=m["id"]))
        assert response.status_code == 201
        for claim in claims:
            assert await prepare(claim) is None
        assert all(row.status == "PENDING" and row.attempts == 0 for row in await records())
        timestamp += timedelta(hours=2)
        await reconcile()
        sent = []

        async def sender(payload):
            sent.append(payload)

        await drain(sender)
        assert {p["email"] for p in sent} == {"ops@example.com", "other@example.com"}


async def test_smtp_inflight_holds_no_monitor_transaction_and_admin_no_recovery(monkeypatch):
    started, finish = asyncio.Event(), asyncio.Event()

    async def sender(payload):
        started.set()
        await finish.wait()

    async with api_client() as api:
        m, _ = await setup(api)
        await sample(api, m["id"], monkeypatch)
        claim = (await claim_deliveries())[0]
        task = asyncio.create_task(dispatch_one(claim, sender))
        await asyncio.wait_for(started.wait(), 3)
        try:
            paused = await asyncio.wait_for(
                api.post(f"/api/monitors/{m['id']}/pause", json={"config_version": 1}), 3
            )
            assert paused.status_code == 200
        finally:
            finish.set()
            await task
        assert (await records())[0].status == "SENT"  # authorized before pause, cannot recall SMTP
        async with Session() as db:
            assert not await db.scalar(select(Event.id).where(Event.event_type == "RECOVERY"))


async def test_dispatcher_cancellation_retains_lease_until_reclaim(monkeypatch):
    started = asyncio.Event()

    async def sender(payload):
        started.set()
        await asyncio.Event().wait()

    async with api_client() as api:
        m, _ = await setup(api)
        await sample(api, m["id"], monkeypatch)
        claim = (await claim_deliveries())[0]
        task = asyncio.create_task(dispatch_one(claim, sender))
        await asyncio.wait_for(started.wait(), 3)
        task.cancel()
        with pytest.raises(asyncio.CancelledError):
            await task
        assert await claim_deliveries() == []
        assert (await records())[0].status == "INFLIGHT"
        async with Session() as db, db.begin():
            row = await db.get(Delivery, claim.id)
            row.lease_until = now() - timedelta(seconds=1)
        await engine.dispose()
        fresh = (await claim_deliveries())[0]
        assert fresh.id == claim.id and fresh.lease_token != claim.lease_token
        assert await prepare(fresh)
        await acknowledge(fresh)
        assert (await records())[0].status == "SENT"


async def test_window_future_start_and_end_boundaries(monkeypatch):
    timestamp = now()
    monkeypatch.setattr("app.maintenance.now", lambda: timestamp)
    async with api_client() as api:
        m = await create(api)
        payload = window(
            monitor_id=m["id"],
            start_at=(timestamp + timedelta(seconds=10)).isoformat(),
            end_at=(timestamp + timedelta(seconds=20)).isoformat(),
        )
        assert (await api.post("/api/maintenance", json=payload)).json()["state"] == "UPCOMING"
        assert not (await api.get("/api/maintenance?state=ACTIVE")).json()["active_monitor_ids"]
        timestamp += timedelta(seconds=10)
        assert (await api.get("/api/maintenance?state=ACTIVE")).json()["active_monitor_ids"] == [
            m["id"]
        ]
        timestamp += timedelta(seconds=10)
        page = (await api.get("/api/maintenance?state=ENDED")).json()
        assert page["items"][0]["state"] == "ENDED" and not page["active_monitor_ids"]
