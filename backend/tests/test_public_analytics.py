import asyncio
import json
import os
import time
import uuid
from datetime import timedelta

import httpx
import pytest
from sqlalchemy import event, select, text
from sqlalchemy.exc import DBAPIError
from test_database import api_client, create
from test_database import database as database

from app.analytics import PERIODS, aggregate
from app.db import Session, engine
from app.models import CheckResult, Monitor, Publication, now
from app.public import app as public_app
from app.public import public_events, readonly

pytestmark = pytest.mark.skipif(not os.environ.get("TEST_DATABASE_URL"), reason="Disposable DB")


def public_client():
    return httpx.AsyncClient(
        transport=httpx.ASGITransport(app=public_app), base_url="http://public"
    )


async def page(api, mid, **changes):
    response = await api.post(
        "/api/status-pages",
        json={
            "slug": "customer-status",
            "title": "Customer status",
            "enabled": True,
            "publications": [{"monitor_id": mid, "public_name": "Customer API"}],
            **changes,
        },
    )
    assert response.status_code == 201, response.text
    return response.json()


@pytest.mark.parametrize("period", list(PERIODS))
async def test_empty_analytics_is_null_not_healthy(period):
    async with api_client() as api:
        monitor = await create(api)
        response = await api.get(f"/api/monitors/{monitor['id']}/analytics?period={period}")
        assert response.status_code == 200, response.text
        data = response.json()
        assert data["uptime_percent"] is None and data["status"] == "NO_DATA"
        assert data["samples"] == 0 and data["coverage_percent"] == 0
        assert len(data["buckets"]) == PERIODS[period][0] // PERIODS[period][1]
        assert all(b["mean_ms"] is None and b["samples"] == 0 for b in data["buckets"])


async def test_postgres_buckets_bounds_gaps_legacy_and_config_versions():
    end = now()
    start = end - timedelta(days=1)
    async with api_client() as api:
        monitor = await create(api)
        mid = uuid.UUID(monitor["id"])
        async with Session() as db, db.begin():
            for offset, success, cadence, version in [
                (-10, True, 30, 1),
                (100, True, 30, 1),
                (160, False, 30, 2),
                (200, True, None, 2),
                (86400, False, 30, 2),
            ]:
                db.add(
                    CheckResult(
                        monitor_id=mid,
                        checked_at=start + timedelta(seconds=offset),
                        success=success,
                        response_ms=20,
                        config_version=version,
                        interval_seconds=cadence,
                    )
                )
        async with Session() as db:
            data = await aggregate(db, mid, "24h", end)
        assert data["samples"] == 3 and data["successful"] == 2
        assert data["uptime_percent"] == pytest.approx(200 / 3)
        assert data["unobserved_seconds"] == 86400 - 80
        assert data["buckets"][0]["coverage_percent"] == pytest.approx(80 / 300 * 100)
        assert data["buckets"][0]["mean_ms"] == 20
        assert all(b["mean_ms"] is None for b in data["buckets"][1:])
        assert (await api.get(f"/api/monitors/{mid}/analytics?period=1y")).status_code == 422
        assert (await api.get(f"/api/monitors/{uuid.uuid4()}/analytics")).status_code == 404


async def test_all_failed_is_zero_uptime_not_no_data():
    async with api_client() as api:
        m = await create(api)
        async with Session() as db, db.begin():
            db.add(
                CheckResult(
                    monitor_id=uuid.UUID(m["id"]),
                    checked_at=now() - timedelta(seconds=10),
                    success=False,
                    response_ms=5000,
                    interval_seconds=30,
                )
            )
        response = await api.get(f"/api/monitors/{m['id']}/analytics")
        data = response.json()
        assert data["status"] == "OBSERVED" and data["uptime_percent"] == 0
        assert data["samples"] == 1 and data["buckets"][-1]["mean_ms"] == 5000


async def test_month_aggregate_is_one_bounded_query_on_dense_fixture(record_testsuite_property):
    end = now()
    async with api_client() as api:
        monitor = await create(api)
        mid = uuid.UUID(monitor["id"])
        async with Session() as db, db.begin():
            await db.execute(
                text("""INSERT INTO check_results
                (id,monitor_id,checked_at,success,status_code,response_ms,error,
                 config_version,interval_seconds)
                SELECT gen_random_uuid(),CAST(:mid AS uuid),
                       CAST(:end AS timestamptz)-interval '30 days'+n*interval '259 seconds',
                       n%10<>0,CASE WHEN n%10<>0 THEN 200 ELSE 500 END,n%500,NULL,1,60
                FROM generate_series(0,9999) AS g(n)"""),
                {"mid": mid, "end": end},
            )
        statements = []

        def executed(connection, cursor, statement, parameters, context, many):
            statements.append(statement)

        event.listen(engine.sync_engine, "before_cursor_execute", executed)
        try:
            started = time.perf_counter()
            async with Session() as db:
                result = await aggregate(db, mid, "30d", end)
            elapsed = time.perf_counter() - started
        finally:
            event.remove(engine.sync_engine, "before_cursor_execute", executed)
        assert len(statements) == 2
        assert statements[0] == "SET LOCAL jit = off"
        assert statements[1].lstrip().startswith("WITH observations AS")
        assert result["samples"] == 10000 and result["successful"] == 9000
        assert result["uptime_percent"] == 90 and len(result["buckets"]) == 360
        assert 20 < result["coverage_percent"] < 25
        record_testsuite_property("month_fixture_rows", 10000)
        record_testsuite_property("month_aggregate_seconds", round(elapsed, 6))
        record_testsuite_property("month_returned_buckets", 360)


@pytest.mark.parametrize(
    "states,expected",
    [
        ([("UP", "FRESH")], "UP"),
        ([("DOWN", "FRESH"), ("UP", "FRESH")], "DOWN"),
        ([("UNKNOWN", "NO_DATA")], "UNKNOWN"),
        ([("PAUSED", "STALE")], "PAUSED"),
        ([("PAUSED", "NO_DATA"), ("PAUSED", "STALE")], "PAUSED"),
        ([("UP", "FRESH"), ("PAUSED", "STALE")], "UP"),
        ([("UP", "FRESH"), ("PAUSED", "NO_DATA")], "UP"),
        ([("UP", "STALE")], "UNKNOWN"),
        ([("DOWN", "STALE")], "DOWN"),
        ([], "NO_DATA"),
    ],
)
async def test_public_health_ignores_paused_freshness(states, expected):
    async with api_client() as api, public_client() as public:
        publications = []
        for index, (state, freshness) in enumerate(states):
            m = await create(api, name=f"Service {index}")
            async with Session() as db, db.begin():
                row = await db.get(Monitor, uuid.UUID(m["id"]))
                row.state = state
                row.last_checked_at = (
                    None
                    if freshness == "NO_DATA"
                    else now() - timedelta(hours=1 if freshness == "STALE" else 0)
                )
            publications.append({"monitor_id": m["id"], "public_name": f"Service {index}"})
        await page(api, None, publications=publications)
        response = await public.get("/api/public/pages/customer-status")
        assert response.status_code == 200
        assert response.json()["state"] == expected
        assert [(s["state"], s["freshness"]) for s in response.json()["services"]] == states


async def test_public_default_private_allowlist_permissions_and_route_isolation():
    async with api_client() as api, public_client() as public:
        m = await create(
            api,
            name="PRIVATE-SENTINEL",
            url="http://example.com/private-secret",
            expected_body="SECRET-BODY",
        )
        hidden = await create(api, name="HIDDEN-SENTINEL")
        disabled = await page(api, m["id"], enabled=False)
        assert (await public.get("/api/public/pages/customer-status")).status_code == 404
        assert (await public.get("/api/public/pages/customer-status/events")).status_code == 404
        update = {k: disabled[k] for k in ("slug", "title", "config_version")}
        publication = {"monitor_id": m["id"], "public_name": "Customer API", "show_history": False}
        response = await api.put(
            f"/api/status-pages/{disabled['id']}",
            json={
                **update,
                "enabled": True,
                "publications": [publication],
            },
        )
        assert response.status_code == 200
        saved = response.json()
        public_id = saved["publications"][0]["id"]
        response = await public.get("/api/public/pages/customer-status")
        assert response.status_code == 200 and response.headers["cache-control"] == "no-store"
        payload = response.json()
        assert set(payload) == {"title", "state", "services"}
        assert set(payload["services"][0]) == {
            "id",
            "name",
            "state",
            "last_checked_at",
            "freshness",
            "maintenance",
            "show_history",
        }
        assert payload["services"][0]["freshness"] == "NO_DATA"
        for forbidden in [
            m["id"],
            hidden["id"],
            "PRIVATE-SENTINEL",
            "HIDDEN-SENTINEL",
            "private-secret",
            "SECRET-BODY",
            "recipients",
            "config_version",
        ]:
            assert forbidden not in response.text
        root = f"/api/public/pages/customer-status/services/{public_id}/analytics"
        assert (await public.get(root)).status_code == 404
        for route in [
            "/api/monitors",
            "/api/overview",
            "/api/events",
            "/api/groups",
            "/api/notifications",
            "/api/maintenance",
            "/api/status-pages",
            "/docs",
            "/openapi.json",
        ]:
            assert (await public.get(route)).status_code == 404
            assert (await public.post(route, json={})).status_code == 404
        assert (await public.post("/api/public/pages/customer-status", json={})).status_code == 405
        publication["show_history"] = True
        granted = await api.put(
            f"/api/status-pages/{saved['id']}",
            json={
                "slug": saved["slug"],
                "title": saved["title"],
                "enabled": True,
                "config_version": saved["config_version"],
                "publications": [publication],
            },
        )
        assert granted.status_code == 200
        assert granted.json()["publications"][0]["id"] == public_id
        assert (await public.get(root)).json()["uptime_percent"] is None
        # Publication editing never resets/fences monitoring state/configuration.
        assert (await api.get(f"/api/monitors/{m['id']}")).json()["config_version"] == 1
        revoked = await api.put(
            f"/api/status-pages/{saved['id']}",
            json={
                "slug": saved["slug"],
                "title": saved["title"],
                "enabled": True,
                "config_version": granted.json()["config_version"],
                "publications": [],
            },
        )
        assert revoked.status_code == 200
        assert (await public.get(root)).status_code == 404
        assert (await public.get("/api/public/pages/customer-status")).json()["services"] == []


async def test_public_sse_revocation_and_readonly_transactions(monkeypatch):
    monkeypatch.setattr("app.public.POLL_SECONDS", 0)

    class Connected:
        async def is_disconnected(self):
            return False

    async with api_client() as api:
        m = await create(api, name="PRIVATE-NAME")
        p = await page(api, m["id"])
        stream = public_events(p["slug"], Connected())
        first = await anext(stream)
        assert first.startswith("event: status\n") and "PRIVATE-NAME" not in first
        assert m["id"] not in first
        async with Session() as db, db.begin():
            publication = await db.scalar(select(Publication))
            await db.delete(publication)
        assert json.loads((await anext(stream)).split("data: ")[1])["services"] == []
        await api.delete(f"/api/status-pages/{p['id']}?config_version=1")
        assert (await anext(stream)).startswith("event: unavailable")
        await stream.aclose()
        with pytest.raises(DBAPIError):
            async with Session() as db:
                await readonly(db)
                await db.execute(text("DELETE FROM monitors"))


async def test_page_crud_conflicts_defaults_and_validation():
    async with api_client() as api:
        m = await create(api)
        response = await api.post("/api/status-pages", json={"slug": "test-page", "title": "Test"})
        assert response.status_code == 201
        p = response.json()
        assert not p["enabled"] and p["publications"] == []
        assert (
            await api.post("/api/status-pages", json={"slug": "test-page", "title": "Test"})
        ).status_code == 409
        for bad in [
            {"slug": "../private"},
            {"title": "  "},
            {
                "publications": [
                    {"monitor_id": m["id"], "public_name": "One"},
                    {"monitor_id": m["id"], "public_name": "Two"},
                ]
            },
        ]:
            result = await api.put(
                f"/api/status-pages/{p['id']}",
                json={
                    "slug": p["slug"],
                    "title": p["title"],
                    "config_version": 1,
                    **bad,
                },
            )
            assert result.status_code == 422
        for version, expected in [(2, 409), (1, 204)]:
            assert (
                await api.delete(f"/api/status-pages/{p['id']}?config_version={version}")
            ).status_code == expected


async def test_parallel_publication_edits_and_monitor_delete_cascade():
    async with api_client() as api, public_client() as public:
        m = await create(api)
        p = await page(api, m["id"])
        update = {
            "slug": p["slug"],
            "title": p["title"],
            "enabled": True,
            "config_version": 1,
            "publications": [{"monitor_id": m["id"], "public_name": "Customer API"}],
        }
        first, second = await asyncio.gather(
            api.put(f"/api/status-pages/{p['id']}", json={**update, "title": "First"}),
            api.put(f"/api/status-pages/{p['id']}", json={**update, "title": "Second"}),
        )
        assert sorted([first.status_code, second.status_code]) == [200, 409]
        saved = (await api.get("/api/status-pages")).json()[0]
        assert saved["config_version"] == 2
        assert saved["publications"][0]["id"] == p["publications"][0]["id"]
        assert (await api.delete(f"/api/monitors/{m['id']}")).status_code == 204
        assert (await public.get(f"/api/public/pages/{p['slug']}")).json()["services"] == []


async def test_public_failures_do_not_disclose_internal_exception(monkeypatch):
    async def failed(db, slug):
        raise RuntimeError("PRIVATE-DATABASE-ERROR-SENTINEL")

    monkeypatch.setattr("app.public.snapshot", failed)
    async with public_client() as public:
        for path in ("/api/public/pages/customer", "/api/public/pages/customer/events"):
            response = await public.get(path)
            assert response.status_code == 503
            assert "PRIVATE-DATABASE-ERROR-SENTINEL" not in response.text
            assert response.json() == {"detail": "Public status temporarily unavailable"}


async def test_dashboard_observed_uptime_and_live_incident_summary(monkeypatch):
    from test_database import sample

    from app.dashboard import live_overview

    async with api_client() as api:
        m = await create(api, failure_threshold=1)
        empty = (await api.get("/api/overview")).json()
        assert empty == {"active_incidents": 0, "opened_at": {}, "uptime_24h": {}}
        await sample(api, m["id"], monkeypatch, True)
        await sample(api, m["id"], monkeypatch)
        overview = (await api.get("/api/overview")).json()
        assert overview["active_incidents"] == 1
        assert overview["uptime_24h"][m["id"]] == {"samples": 2, "percent": 50}
        assert m["id"] in overview["opened_at"]
        await sample(api, m["id"], monkeypatch, True)
        async with Session() as db:
            assert await live_overview(db) == {"active_incidents": 0, "opened_at": {}}


async def test_analytics_jit_setting_is_transaction_local():
    async with Session() as db:
        baseline = await db.scalar(text("SHOW jit"))
        await aggregate(db, uuid.uuid4(), "30d")
        assert await db.scalar(text("SHOW jit")) == "off"
        await db.rollback()
        assert await db.scalar(text("SHOW jit")) == baseline
