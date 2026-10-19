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
