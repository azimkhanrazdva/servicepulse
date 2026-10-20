import asyncio
import os
from datetime import timedelta

import httpx
import pytest
import pytest_asyncio
from sqlalchemy import func, select

from app.checker import Observation
from app.db import Session, engine
from app.main import app
from app.models import Base, CheckResult, Incident, Monitor, now
from app.worker import claim_due, execute

pytestmark = pytest.mark.skipif(
    not os.environ.get("TEST_DATABASE_URL"), reason="Requires disposable TEST_DATABASE_URL"
)


@pytest_asyncio.fixture(autouse=True)
async def database():
    if not os.environ.get("TEST_DATABASE_URL"):
        yield
        return
    assert os.environ["TEST_DATABASE_URL"].endswith("/servicepulse_test")
    assert str(engine.url).endswith("/servicepulse_test")
    async with engine.begin() as connection:
        await connection.run_sync(Base.metadata.drop_all)
        await connection.run_sync(Base.metadata.create_all)
    yield
    await engine.dispose()


async def test_create_claim_execute_read_delete(monkeypatch):
    async def observed(monitor, client):
        return Observation(True, 200, 12.5, None)

    monkeypatch.setattr("app.worker.check", observed)
    async with httpx.AsyncClient(
        transport=httpx.ASGITransport(app=app), base_url="http://test"
    ) as api:
        response = await api.post(
            "/api/monitors", json={"name": "demo", "url": "http://example.com"}
        )
        assert response.status_code == 201
        monitor_id = response.json()["id"]
        claimed = await claim_due(50)
        assert len(claimed) == 1
        assert await claim_due(50) == []
        assert (await api.post(f"/api/monitors/{monitor_id}/run")).status_code == 409
        await execute(claimed[0], None)
        saved = (await api.get(f"/api/monitors/{monitor_id}")).json()
        assert saved["state"] == "UP" and saved["last_status_code"] == 200
        history = (await api.get(f"/api/monitors/{monitor_id}/results")).json()
        assert len(history) == 1 and history[0]["response_ms"] == 12.5
        assert (await api.delete(f"/api/monitors/{monitor_id}")).status_code == 204
        assert (await api.get(f"/api/monitors/{monitor_id}")).status_code == 404
    async with Session() as db:
        assert await db.scalar(select(func.count()).select_from(CheckResult)) == 0


async def test_expired_lease_fences_stale_result(monkeypatch):
    async with Session() as db, db.begin():
        db.add(Monitor(name="lease", url="https://example.com"))
    old = (await claim_due(1))[0]
    async with Session() as db, db.begin():
        row = await db.get(Monitor, old.id)
        row.lease_until = now() - timedelta(seconds=1)
    fresh = (await claim_due(1))[0]
    assert fresh.lease_token != old.lease_token

    async def observed(*args):
        return Observation(True, 200, 1, None)

    monkeypatch.setattr("app.worker.check", observed)
    await execute(old, None)
    async with Session() as db:
        assert await db.scalar(select(func.count()).select_from(CheckResult)) == 0
    await execute(fresh, None)
    async with Session() as db:
        assert await db.scalar(select(func.count()).select_from(CheckResult)) == 1


async def test_competing_claims_are_disjoint():
    import asyncio

    async with Session() as db, db.begin():
        db.add_all([Monitor(name=str(i), url="http://example.com") for i in range(50)])
    first, second = await asyncio.gather(claim_due(50), claim_due(50))
    ids = [m.id for m in first + second]
    assert len(ids) == len(set(ids)) == 50


async def test_api_rejects_invalid_settings():
    async with httpx.AsyncClient(
        transport=httpx.ASGITransport(app=app), base_url="http://test"
    ) as api:
        response = await api.post("/api/monitors", json={"name": "test", "url": "file:///tmp/a"})
        assert response.status_code == 422
        assert (await api.get("/api/monitors/not-a-uuid")).status_code == 422


def api_client():
    return httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url="http://test")


async def create(api, **fields):
    response = await api.post(
        "/api/monitors",
        json={
            "name": "Managed",
            "url": "http://example.com",
            **fields,
        },
    )
    assert response.status_code == 201, response.text
    return response.json()


async def sample(api, monitor_id, monkeypatch, success=False):
    async def observed(*args):
        return Observation(
            success, 200 if success else 500, 2, None if success else "unexpected_status"
        )

    monkeypatch.setattr("app.worker.check", observed)
    assert (await api.post(f"/api/monitors/{monitor_id}/run")).status_code == 202
    claimed = await claim_due(50)
    target = next(m for m in claimed if str(m.id) == monitor_id)
    await execute(target, None)


async def test_incident_threshold_recovery_timestamps_and_pagination(monkeypatch):
    from datetime import datetime

    timestamp = now() + timedelta(days=1)
    monkeypatch.setattr("app.worker.now", lambda: timestamp)
    monkeypatch.setattr("app.incidents.now", lambda: timestamp)
    async with api_client() as api:
        m = await create(api)
        mid = m["id"]
        await sample(api, mid, monkeypatch, True)
        await sample(api, mid, monkeypatch)
        assert (await api.get(f"/api/monitors/{mid}")).json()["state"] == "UP"
        assert (await api.get("/api/incidents")).json()["items"] == []
        timestamp += timedelta(seconds=15)
        await sample(api, mid, monkeypatch)
        opened = (await api.get("/api/incidents/active")).json()["items"][0]
        assert datetime.fromisoformat(opened["opened_at"].replace("Z", "+00:00")) == timestamp
        assert opened["duration_seconds"] == 0
        await sample(api, mid, monkeypatch)
        assert len((await api.get("/api/incidents")).json()["items"]) == 1
        timestamp += timedelta(seconds=42)
        assert (await api.get(f"/api/incidents/{opened['id']}")).json()["duration_seconds"] == 42
        await sample(api, mid, monkeypatch, True)
        await sample(api, mid, monkeypatch, True)
        closed = (await api.get(f"/api/monitors/{mid}/incidents")).json()["items"][0]
        assert closed["state"] == "CLOSED" and closed["closure_reason"] == "RECOVERED"
        assert closed["duration_seconds"] == 42 and closed["closed_at"] == closed["recovered_at"]
        assert (await api.get("/api/incidents/active")).json()["items"] == []
        await sample(api, mid, monkeypatch)
        await sample(api, mid, monkeypatch)
        page = (await api.get("/api/incidents?limit=1&order=asc")).json()
        assert page["has_more"] and page["items"][0]["id"] == opened["id"]
        assert len((await api.get("/api/incidents?state=CLOSED")).json()["items"]) == 1
        assert len((await api.get("/api/incidents?limit=1&offset=1")).json()["items"]) == 1
        assert (await api.get("/api/incidents?since=2030-01-01T00:00:00Z")).json()["items"] == []


@pytest.mark.parametrize("operation,reason", [("pause", "PAUSED"), ("edit", "CONFIG_CHANGED")])
async def test_administrative_closure_and_new_incident(monkeypatch, operation, reason):
    async with api_client() as api:
        m = await create(api, failure_threshold=1)
        mid = m["id"]
        root = f"/api/monitors/{mid}"
        await sample(api, mid, monkeypatch)
        if operation == "pause":
            assert (await api.post(root + "/pause", json={"config_version": 1})).status_code == 200
            assert (await api.post(root + "/resume", json={"config_version": 2})).status_code == 200
        else:
            assert (await api.put(root, json=edit_payload(m, name="Renamed"))).status_code == 200
        closed = (await api.get("/api/incidents")).json()["items"][0]
        assert closed["closure_reason"] == reason and closed["recovered_at"] is None
        assert closed["closed_at"] is not None
        assert (await api.get(root)).json()["state"] == "UNKNOWN"
        await sample(api, mid, monkeypatch)
        rows = (await api.get("/api/incidents")).json()["items"]
        assert len(rows) == 2 and sum(i["state"] == "OPEN" for i in rows) == 1
        await api.delete(root)
        assert (await api.get("/api/incidents")).json()["items"] == []


@pytest.mark.parametrize(
    "query",
    [
        "limit=101",
        "offset=-1",
        "state=BAD",
        "order=no",
        "monitor_id=bad",
        "since=2026-10-19",
        "since=2026-10-20T00:00:00Z&until=2026-10-19T00:00:00Z",
    ],
)
async def test_incident_query_validation(query):
    async with api_client() as api:
        assert (await api.get("/api/incidents?" + query)).status_code == 422


async def test_incident_legacy_down_no_fictional_recovery(monkeypatch):
    async with api_client() as api:
        m = await create(api)
        import uuid

        async with Session() as db, db.begin():
            row = await db.get(Monitor, uuid.UUID(m["id"]))
            row.state, row.consecutive_failures = "DOWN", 4
        await sample(api, m["id"], monkeypatch, True)
        assert (await api.get("/api/incidents")).json()["items"] == []
        async with Session() as db, db.begin():
            row = await db.get(Monitor, uuid.UUID(m["id"]))
            row.state, row.consecutive_failures = "DOWN", 4
        await sample(api, m["id"], monkeypatch)
        await sample(api, m["id"], monkeypatch)
        assert len((await api.get("/api/incidents/active")).json()["items"]) == 1


async def test_incident_database_constraints():
    from sqlalchemy.exc import IntegrityError

    async with Session() as db, db.begin():
        monitor = Monitor(name="constraint", url="https://example.com")
        db.add(monitor)
        await db.flush()
        mid = monitor.id
        db.add(Incident(monitor_id=mid, opened_at=now()))
    with pytest.raises(IntegrityError):
        async with Session() as db, db.begin():
            db.add(Incident(monitor_id=mid, opened_at=now()))
    with pytest.raises(IntegrityError):
        async with Session() as db, db.begin():
            db.add(
                Incident(
                    monitor_id=mid,
                    opened_at=now(),
                    closed_at=now(),
                    closure_reason="PAUSED",
                    recovered_at=now(),
                )
            )


async def test_postgres_failure_rolls_back_result_state_and_incident(monkeypatch):
    from sqlalchemy import text
    from sqlalchemy.exc import DBAPIError

    from app.incidents import observe_incident

    async def fail_after_flush(db, *args):
        await observe_incident(db, *args)
        await db.flush()
        await db.execute(text("SELECT 1/0"))

    monkeypatch.setattr("app.worker.observe_incident", fail_after_flush)
    async with api_client() as api:
        m = await create(api, failure_threshold=1)
        with pytest.raises(DBAPIError):
            await sample(api, m["id"], monkeypatch)
        assert (await api.get(f"/api/monitors/{m['id']}")).json()["state"] == "UNKNOWN"
        assert (await api.get(f"/api/monitors/{m['id']}/results")).json() == []
        assert (await api.get("/api/incidents")).json()["items"] == []
        monkeypatch.setattr("app.worker.observe_incident", observe_incident)
        async with Session() as db, db.begin():
            import uuid

            row = await db.get(Monitor, uuid.UUID(m["id"]))
            row.lease_until = now() - timedelta(seconds=1)
        fresh = (await claim_due(1))[0]
        await execute(fresh, None)
        assert len((await api.get("/api/incidents")).json()["items"]) == 1


async def test_expiry_during_http_old_success_cannot_close_new_incident(monkeypatch):
    started, release = asyncio.Event(), asyncio.Event()

    async def slow(*args):
        started.set()
        await release.wait()
        return Observation(True, 200, 1, None)

    async with Session() as db, db.begin():
        db.add(Monitor(name="old", url="https://example.com", failure_threshold=1))
    old = (await claim_due(1))[0]
    monkeypatch.setattr("app.worker.check", slow)
    task = asyncio.create_task(execute(old, None))
    await started.wait()
    async with Session() as db, db.begin():
        row = await db.get(Monitor, old.id)
        row.lease_until = now() - timedelta(seconds=1)
    fresh = (await claim_due(1))[0]

    async def failed(*args):
        return Observation(False, 500, 1, "unexpected_status")

    monkeypatch.setattr("app.worker.check", failed)
    await execute(fresh, None)
    release.set()
    await task
    await execute(fresh, None)  # same completion retry cannot commit twice
    async with Session() as db:
        assert (await db.get(Monitor, old.id)).state == "DOWN"
        assert await db.scalar(select(func.count()).select_from(CheckResult)) == 1
        assert await db.scalar(select(func.count()).select_from(Incident)) == 1
        assert (await db.scalar(select(Incident))).closed_at is None


async def test_slow_beyond_interval_nonblocking_and_cancellation(monkeypatch):
    started, release = asyncio.Event(), asyncio.Event()

    async def slow(monitor, client):
        if monitor.name == "slow":
            started.set()
            await release.wait()
        return Observation(True, 200, 1, None)

    monkeypatch.setattr("app.worker.check", slow)
    async with Session() as db, db.begin():
        db.add_all(
            [
                Monitor(name=name, url="https://example.com", timeout_seconds=60)
                for name in ("slow", "fast")
            ]
        )
    claims = await claim_due(2)
    slow_row = next(m for m in claims if m.name == "slow")
    task = asyncio.create_task(execute(slow_row, None))
    await started.wait()
    clock = now() + timedelta(seconds=31)
    monkeypatch.setattr("app.worker.now", lambda: clock)
    assert await claim_due(2) == []  # interval elapsed, active HTTP lease still owned
    await execute(next(m for m in claims if m.name == "fast"), None)
    task.cancel()
    with pytest.raises(asyncio.CancelledError):
        await task
    async with Session() as db:
        assert (await db.get(Monitor, slow_row.id)).state == "UNKNOWN"
        assert await db.scalar(select(func.count()).select_from(CheckResult)) == 1
        assert await db.scalar(select(func.count()).select_from(Incident)) == 0


async def test_incident_pagination_has_one_join_no_n_plus_one():
    from sqlalchemy import event

    async with Session() as db, db.begin():
        monitor = Monitor(name="journal", url="https://example.com")
        db.add(monitor)
        await db.flush()
        timestamp = now()
        db.add_all(
            [
                Incident(
                    monitor_id=monitor.id,
                    opened_at=timestamp - timedelta(minutes=i + 1),
                    closed_at=timestamp,
                    recovered_at=timestamp,
                    closure_reason="RECOVERED",
                )
                for i in range(150)
            ]
        )
    statements = []

    def count_sql(conn, cursor, statement, parameters, context, executemany):
        statements.append(statement)

    event.listen(engine.sync_engine, "before_cursor_execute", count_sql)
    try:
        async with api_client() as api:
            response = await api.get("/api/incidents?limit=100")
            assert response.status_code == 200
            assert len(response.json()["items"]) == 100 and response.json()["has_more"]
            assert len(statements) == 1 and "JOIN monitors" in statements[0]
            second = (await api.get("/api/incidents?limit=100&offset=100")).json()
            assert len(second["items"]) == 50 and not second["has_more"]
            assert not (
                {r["id"] for r in response.json()["items"]} & {r["id"] for r in second["items"]}
            )
    finally:
        event.remove(engine.sync_engine, "before_cursor_execute", count_sql)


async def test_competing_completion_retry_creates_one_result_and_incident(monkeypatch):
    arrived, release = asyncio.Event(), asyncio.Event()
    calls = 0

    async def observed(*args):
        nonlocal calls
        calls += 1
        if calls == 2:
            arrived.set()
        await release.wait()
        return Observation(False, 500, 1, "unexpected_status")

    monkeypatch.setattr("app.worker.check", observed)
    async with Session() as db, db.begin():
        db.add(Monitor(name="retry", url="https://example.com", failure_threshold=1))
    claimed = (await claim_due(1))[0]
    tasks = [asyncio.create_task(execute(claimed, None)) for _ in range(2)]
    await asyncio.wait_for(arrived.wait(), 3)
    release.set()
    await asyncio.gather(*tasks)
    async with Session() as db:
        assert await db.scalar(select(func.count()).select_from(CheckResult)) == 1
        assert await db.scalar(select(func.count()).select_from(Incident)) == 1
        assert (await db.get(Monitor, claimed.id)).consecutive_failures == 1


async def test_incident_missing_resources_are_404():
    import uuid

    async with api_client() as api:
        for path in [f"/api/incidents/{uuid.uuid4()}", f"/api/monitors/{uuid.uuid4()}/incidents"]:
            assert (await api.get(path)).status_code == 404


def edit_payload(monitor, **fields):
    keys = (
        "name",
        "url",
        "interval_seconds",
        "timeout_seconds",
        "expected_status",
        "expected_body",
        "failure_threshold",
        "config_version",
    )
    return {**{key: monitor[key] for key in keys}, **fields}


async def test_monitor_crud_pause_resume_and_manual_queue():
    async with api_client() as api:
        m = await create(api)
        root = f"/api/monitors/{m['id']}"
        paused = await api.post(root + "/pause", json={"config_version": 1})
        assert paused.status_code == 200 and paused.json()["state"] == "PAUSED"
        assert await claim_due(50) == []
        assert (await api.post(root + "/run")).status_code == 409
        updated = await api.put(
            root,
            json=edit_payload(
                paused.json(), interval_seconds=3600, url="https://example.org", name="Changed"
            ),
        )
        assert updated.status_code == 200 and updated.json()["state"] == "PAUSED"
        assert updated.json()["config_version"] == 3
        assert (await api.post(root + "/resume", json={"config_version": 2})).status_code == 409
        resumed = await api.post(root + "/resume", json={"config_version": 3})
        assert resumed.json()["state"] == "UNKNOWN"
        assert (await api.post(root + "/run")).status_code == 202
        assert (await api.post(root + "/run")).status_code == 409
        claimed = (await claim_due(1))[0]
        assert claimed.url == "https://example.org" and claimed.interval_seconds == 3600
        assert (await api.delete(root + "?config_version=1")).status_code == 409
        assert (await api.delete(root + "?config_version=4")).status_code == 204
        assert await claim_due(50) == []


@pytest.mark.parametrize("action", ["edit", "pause", "delete", "pause_resume"])
@pytest.mark.parametrize("success", [True, False])
async def test_mutation_during_http_does_not_commit_stale_result(monkeypatch, action, success):
    started, finish = asyncio.Event(), asyncio.Event()

    async def delayed(*args):
        started.set()
        await finish.wait()
        return Observation(success, 200 if success else 500, 100, None)

    monkeypatch.setattr("app.worker.check", delayed)
    async with api_client() as api:
        m = await create(api)
        root = f"/api/monitors/{m['id']}"
        claimed = (await claim_due(1))[0]
        task = asyncio.create_task(execute(claimed, None))
        try:
            await asyncio.wait_for(started.wait(), 3)
            if action == "edit":
                response = await api.put(
                    root, json=edit_payload(m, url="http://example.org", interval_seconds=60)
                )
            elif action == "delete":
                response = await api.delete(root)
            else:
                response = await api.post(root + "/pause", json={"config_version": 1})
                if action == "pause_resume":
                    response = await api.post(root + "/resume", json={"config_version": 2})
            assert response.status_code in {200, 204}
            assert await claim_due(50) == []  # active lease retained even after pause/resume/edit
        finally:
            finish.set()
            await task
        async with Session() as db:
            assert await db.scalar(select(func.count()).select_from(CheckResult)) == 0
            assert await db.scalar(select(func.count()).select_from(Incident)) == 0
        due = await claim_due(1)
        assert bool(due) == (action in {"edit", "pause_resume"})
        if action == "edit":
            assert due[0].url == "http://example.org" and due[0].config_version == 2


async def test_mutation_before_http_prevents_old_network_request(monkeypatch):
    called = False

    async def observed(*args):
        nonlocal called
        called = True
        return Observation(True, 200, 1, None)

    monkeypatch.setattr("app.worker.check", observed)
    async with api_client() as api:
        m = await create(api)
        claimed = (await claim_due(1))[0]
        await api.put(f"/api/monitors/{m['id']}", json=edit_payload(m, url="https://example.org"))
        await execute(claimed, None)
        assert not called
        assert len(await claim_due(1)) == 1


async def test_two_clients_edit_same_version_one_conflicts():
    async with api_client() as api:
        m = await create(api)
        root = f"/api/monitors/{m['id']}"
        replies = await asyncio.gather(
            *[api.put(root, json=edit_payload(m, name=name)) for name in ["Client A", "Client B"]]
        )
        assert sorted(r.status_code for r in replies) == [200, 409]
        saved = (await api.get(root)).json()
        assert saved["name"] in {"Client A", "Client B"} and saved["config_version"] == 2


async def test_interval_and_timeout_used_after_edit(monkeypatch):
    async def observed(m, _):
        assert (
            m.timeout_seconds == 7 and m.expected_status == 204 and m.expected_body == "  exact  "
        )
        return Observation(True, 204, 1, None)

    monkeypatch.setattr("app.worker.check", observed)
    async with api_client() as api:
        m = await create(api)
        reply = await api.put(
            f"/api/monitors/{m['id']}",
            json=edit_payload(
                m,
                interval_seconds=90,
                timeout_seconds=7,
                expected_status=204,
                expected_body="  exact  ",
            ),
        )
        assert reply.status_code == 200
        await execute((await claim_due(1))[0], None)
        async with Session() as db:
            row = await db.get(Monitor, m["id"])
            assert 89 < (row.next_due_at - now()).total_seconds() <= 90
            result = await db.scalar(select(CheckResult))
            assert result.config_version == 2


async def test_groups_crud_membership_recipients_and_cascades():
    async with api_client() as api:
        m = await create(api)
        response = await api.post(
            "/api/groups",
            json={
                "name": "Platform",
                "monitor_ids": [m["id"], m["id"]],
                "recipients": ["ops@example.com", "ops@example.com"],
            },
        )
        assert response.status_code == 201, response.text
        group = response.json()
        root = f"/api/groups/{group['id']}"
        assert group["state"] == "UNKNOWN" and group["monitor_ids"] == [m["id"]]
        assert group["recipients"] == ["ops@example.com"]
        await api.post(f"/api/monitors/{m['id']}/pause", json={"config_version": 1})
        assert (await api.get(root)).json()["state"] == "PAUSED"
        changed = await api.put(
            root, json={"name": "Empty", "config_version": 1, "monitor_ids": [], "recipients": []}
        )
        assert changed.status_code == 200 and changed.json()["state"] == "UNKNOWN"
        assert (await api.put(root, json={"name": "Stale", "config_version": 1})).status_code == 409
        readd = await api.put(
            root, json={"name": "Platform", "config_version": 2, "monitor_ids": [m["id"]]}
        )
        assert readd.status_code == 200
        await api.delete(f"/api/monitors/{m['id']}")
        assert (await api.get(root)).json()["monitor_ids"] == []
        assert (await api.delete(root + "?config_version=3")).status_code == 204
        assert (await api.get(root)).status_code == 404


@pytest.mark.parametrize(
    "fields",
    [
        {"name": " "},
        {"name": "Group", "recipients": ["bad"]},
        {"name": "Group", "monitor_ids": ["00000000-0000-0000-0000-000000000001"]},
    ],
)
async def test_invalid_group_rejected(fields):
    async with api_client() as api:
        assert (await api.post("/api/groups", json=fields)).status_code == 422
        assert (await api.get("/api/groups")).json() == []


async def test_group_and_monitor_concurrent_updates_do_not_lose_fields():
    async with api_client() as api:
        m = await create(api)
        group = (
            await api.post("/api/groups", json={"name": "Group", "monitor_ids": [m["id"]]})
        ).json()
        replies = await asyncio.gather(
            api.put(f"/api/monitors/{m['id']}", json=edit_payload(m, name="New monitor")),
            api.put(
                f"/api/groups/{group['id']}",
                json={
                    "name": "New group",
                    "config_version": 1,
                    "monitor_ids": [m["id"]],
                    "recipients": ["team@example.com"],
                },
            ),
        )
        assert [r.status_code for r in replies] == [200, 200]
        await engine.dispose()  # new connections still read persisted configuration
        assert (await api.get(f"/api/monitors/{m['id']}")).json()["name"] == "New monitor"
        saved = (await api.get(f"/api/groups/{group['id']}")).json()
        assert saved["name"] == "New group" and saved["recipients"] == ["team@example.com"]


async def test_database_rejects_out_of_range_interval():
    from sqlalchemy.exc import IntegrityError

    with pytest.raises(IntegrityError):
        async with Session() as db, db.begin():
            db.add(Monitor(name="Invalid", url="https://example.com", interval_seconds=29))


async def test_manual_queue_not_lost_by_late_completion(monkeypatch):
    async def observed(*args):
        return Observation(True, 200, 1, None)

    monkeypatch.setattr("app.worker.check", observed)
    async with api_client() as api:
        monitor = await create(api)
        claimed = (await claim_due(1))[0]
        async with Session() as db, db.begin():
            row = await db.get(Monitor, claimed.id)
            row.lease_until = now() - timedelta(seconds=1)
        assert (await api.post(f"/api/monitors/{monitor['id']}/run")).status_code == 202
        await execute(claimed, None)
        saved = (await api.get(f"/api/monitors/{monitor['id']}")).json()
        assert saved["run_requested"]
        assert len(await claim_due(1)) == 1
