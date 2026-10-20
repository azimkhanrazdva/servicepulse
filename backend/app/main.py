import asyncio
import json
import uuid
from typing import Annotated

from fastapi import Depends, FastAPI, HTTPException, Query, Request
from fastapi.responses import StreamingResponse
from sqlalchemy import select, text
from sqlalchemy.ext.asyncio import AsyncSession
from starlette.middleware.trustedhost import TrustedHostMiddleware

from app.analytics import router as analytics_router
from app.dashboard import live_overview
from app.dashboard import router as dashboard_router
from app.db import Session, session_dependency
from app.groups import group_snapshots, require_version
from app.groups import router as groups_router
from app.incidents import close_incident, incident_page
from app.incidents import router as incidents_router
from app.maintenance import router as maintenance_router
from app.maintenance import window_snapshot
from app.models import CheckResult, Monitor, now
from app.notifications import router as notifications_router
from app.publication import router as publication_router
from app.schemas import MonitorCreate, MonitorRead, MonitorUpdate, ResultRead, VersionRequest

app = FastAPI(title="ServicePulse", version="0.5.0")
app.add_middleware(TrustedHostMiddleware, allowed_hosts=["localhost", "127.0.0.1", "backend"])
app.include_router(analytics_router)
app.include_router(publication_router)
app.include_router(dashboard_router)
app.include_router(groups_router)
app.include_router(incidents_router)
app.include_router(maintenance_router)
app.include_router(notifications_router)
DB = Annotated[AsyncSession, Depends(session_dependency)]


@app.get("/api/health")
async def health():
    return {"status": "ok"}


@app.get("/api/ready")
async def ready(db: DB):
    await db.execute(text("SELECT 1 FROM monitors LIMIT 1"))
    return {"status": "ready"}


@app.get("/api/monitors", response_model=list[MonitorRead])
async def monitors(db: DB):
    return (await db.scalars(select(Monitor).order_by(Monitor.created_at).limit(500))).all()


@app.post("/api/monitors", response_model=MonitorRead, status_code=201)
async def create_monitor(payload: MonitorCreate, db: DB):
    monitor = Monitor(**payload.model_dump())
    db.add(monitor)
    await db.commit()
    return monitor


async def find_monitor(db, monitor_id, lock=False):
    stmt = select(Monitor).where(Monitor.id == monitor_id)
    if lock:
        stmt = stmt.with_for_update()
    monitor = await db.scalar(stmt)
    if monitor is None:
        raise HTTPException(404, "Monitor not found")
    return monitor


@app.get("/api/monitors/{monitor_id}", response_model=MonitorRead)
async def detail(monitor_id: uuid.UUID, db: DB):
    return await find_monitor(db, monitor_id)


@app.delete("/api/monitors/{monitor_id}", status_code=204)
async def delete_monitor(
    monitor_id: uuid.UUID, db: DB, config_version: Annotated[int | None, Query(ge=1)] = None
):
    monitor = await find_monitor(db, monitor_id, lock=True)
    if config_version is not None:
        require_version(monitor, config_version)
    await db.delete(monitor)
    await db.commit()


@app.put("/api/monitors/{monitor_id}", response_model=MonitorRead)
async def update_monitor(monitor_id: uuid.UUID, payload: MonitorUpdate, db: DB):
    monitor = await find_monitor(db, monitor_id, lock=True)
    require_version(monitor, payload.config_version)
    await close_incident(db, monitor.id, "CONFIG_CHANGED", now())
    for key, value in payload.model_dump(exclude={"config_version"}).items():
        setattr(monitor, key, value)
    monitor.config_version += 1
    monitor.state = "PAUSED" if monitor.state == "PAUSED" else "UNKNOWN"
    monitor.consecutive_failures = 0
    monitor.last_checked_at = monitor.last_status_code = monitor.last_response_ms = None
    monitor.next_due_at = now()
    monitor.run_requested = False
    await db.commit()
    return monitor


@app.post("/api/monitors/{monitor_id}/pause", response_model=MonitorRead)
async def pause_monitor(monitor_id: uuid.UUID, payload: VersionRequest, db: DB):
    monitor = await find_monitor(db, monitor_id, lock=True)
    require_version(monitor, payload.config_version)
    await close_incident(db, monitor.id, "PAUSED", now())
    monitor.state = "PAUSED"
    monitor.consecutive_failures = 0
    monitor.config_version += 1
    monitor.run_requested = False
    await db.commit()
    return monitor


@app.post("/api/monitors/{monitor_id}/resume", response_model=MonitorRead)
async def resume_monitor(monitor_id: uuid.UUID, payload: VersionRequest, db: DB):
    monitor = await find_monitor(db, monitor_id, lock=True)
    require_version(monitor, payload.config_version)
    if monitor.state != "PAUSED":
        raise HTTPException(409, "Monitor is not paused")
    monitor.state = "UNKNOWN"
    monitor.consecutive_failures = 0
    monitor.config_version += 1
    monitor.next_due_at = now()
    await db.commit()
    return monitor


@app.post("/api/monitors/{monitor_id}/run", status_code=202)
async def run_now(monitor_id: uuid.UUID, db: DB):
    monitor = await find_monitor(db, monitor_id, lock=True)
    if monitor.state == "PAUSED" or monitor.is_running or monitor.run_requested:
        raise HTTPException(409, "Monitor is paused, already queued or running")
    monitor.next_due_at = now()
    monitor.run_requested = True
    await db.commit()
    return {"status": "queued"}


@app.get("/api/monitors/{monitor_id}/results", response_model=list[ResultRead])
async def results(monitor_id: uuid.UUID, db: DB):
    await find_monitor(db, monitor_id)
    return (
        await db.scalars(
            select(CheckResult)
            .where(CheckResult.monitor_id == monitor_id)
            .order_by(CheckResult.checked_at.desc())
            .limit(100)
        )
    ).all()


@app.get("/api/events")
async def events(request: Request):
    async def stream():
        while not await request.is_disconnected():
            async with Session() as db:
                await db.connection(execution_options={"isolation_level": "REPEATABLE READ"})
                rows = (
                    await db.scalars(select(Monitor).order_by(Monitor.created_at).limit(500))
                ).all()
                data = [MonitorRead.model_validate(row).model_dump(mode="json") for row in rows]
                groups = [row.model_dump(mode="json") for row in await group_snapshots(db)]
                incidents = (await incident_page(db)).model_dump(mode="json")
                maintenance = await window_snapshot(db)
                overview = await live_overview(db)
            yield f"data: {json.dumps(data)}\n\n"
            yield f"event: groups\ndata: {json.dumps(groups)}\n\n"
            yield f"event: incidents\ndata: {json.dumps(incidents)}\n\n"
            yield f"event: maintenance\ndata: {json.dumps(maintenance)}\n\n"
            yield f"event: overview\ndata: {json.dumps(overview, default=str)}\n\n"
            await asyncio.sleep(2)

    return StreamingResponse(
        stream(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "X-Accel-Buffering": "no",
        },
    )
