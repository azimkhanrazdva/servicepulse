import asyncio
import json
import uuid
from typing import Annotated

from fastapi import Depends, FastAPI, HTTPException, Request
from fastapi.responses import StreamingResponse
from sqlalchemy import select, text
from sqlalchemy.ext.asyncio import AsyncSession

from app.db import Session, session_dependency
from app.models import CheckResult, Monitor, now
from app.schemas import MonitorCreate, MonitorRead, ResultRead

app = FastAPI(title="ServicePulse", version="0.1.0")
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
async def delete_monitor(monitor_id: uuid.UUID, db: DB):
    monitor = await find_monitor(db, monitor_id, lock=True)
    await db.delete(monitor)
    await db.commit()


@app.post("/api/monitors/{monitor_id}/run", status_code=202)
async def run_now(monitor_id: uuid.UUID, db: DB):
    monitor = await find_monitor(db, monitor_id, lock=True)
    if monitor.state == "PAUSED" or (monitor.lease_until and monitor.lease_until > now()):
        raise HTTPException(409, "Monitor is paused or already running")
    monitor.next_due_at = now()
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
                rows = (
                    await db.scalars(select(Monitor).order_by(Monitor.created_at).limit(500))
                ).all()
                data = [MonitorRead.model_validate(row).model_dump(mode="json") for row in rows]
            yield f"data: {json.dumps(data)}\n\n"
            await asyncio.sleep(2)

    return StreamingResponse(
        stream(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "X-Accel-Buffering": "no",
        },
    )
