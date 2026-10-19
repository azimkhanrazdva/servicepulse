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
from app.models import Base, CheckResult, Monitor, now
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
async def test_mutation_during_http_does_not_commit_stale_result(monkeypatch, action):
    started, finish = asyncio.Event(), asyncio.Event()

    async def delayed(*args):
        started.set()
        await finish.wait()
        return Observation(True, 200, 100, None)

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
