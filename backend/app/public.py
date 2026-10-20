"""Standalone read-only public ASGI surface. Never register management routers here."""

import asyncio
import json
import uuid

from fastapi import FastAPI, HTTPException, Request
from fastapi.encoders import jsonable_encoder
from fastapi.responses import JSONResponse, StreamingResponse
from sqlalchemy import or_, select, text

from app.analytics import Period, aggregate
from app.db import Session
from app.models import MaintenanceWindow, Monitor, MonitorGroup, Publication, PublicPage, now

app = FastAPI(openapi_url=None, docs_url=None, redoc_url=None)
POLL_SECONDS = 2


@app.middleware("http")
async def public_headers(request, call_next):
    try:
        response = await call_next(request)
    except Exception:
        response = JSONResponse(
            {"detail": "Public status temporarily unavailable"}, status_code=503
        )
    response.headers["Cache-Control"] = "no-store"
    response.headers["X-Content-Type-Options"] = "nosniff"
    return response


async def readonly(db):
    await db.connection(execution_options={"isolation_level": "REPEATABLE READ"})
    await db.execute(text("SET TRANSACTION READ ONLY"))


async def snapshot(db, slug):
    page = await db.scalar(select(PublicPage).where(PublicPage.slug == slug, PublicPage.enabled))
    if page is None:
        raise HTTPException(404, "Status page not found")
    # Explicit columns and explicit JSON allowlist; no ORM/private-schema serialization.
    rows = (
        await db.execute(
            select(
                Publication.id,
                Publication.public_name,
                Publication.show_history,
                Monitor.id.label("internal_id"),
                Monitor.state,
                Monitor.last_checked_at,
                Monitor.interval_seconds,
                Monitor.timeout_seconds,
            )
            .join(Monitor, Monitor.id == Publication.monitor_id)
            .where(Publication.page_id == page.id)
            .order_by(Publication.public_name, Publication.id)
        )
    ).all()
    timestamp = now()
    ids = [r.internal_id for r in rows]
    related_groups = select(MonitorGroup.group_id).where(MonitorGroup.monitor_id.in_(ids))
    active = select(MaintenanceWindow.monitor_id, MaintenanceWindow.group_id).where(
        MaintenanceWindow.start_at <= timestamp,
        MaintenanceWindow.end_at > timestamp,
        or_(MaintenanceWindow.monitor_id.in_(ids), MaintenanceWindow.group_id.in_(related_groups)),
    )
    windows = (await db.execute(active)).all()
    maintained = {w.monitor_id for w in windows if w.monitor_id}
    groups = {w.group_id for w in windows if w.group_id}
    if groups:
        maintained.update(
            (
                await db.scalars(
                    select(MonitorGroup.monitor_id).where(
                        MonitorGroup.group_id.in_(groups), MonitorGroup.monitor_id.in_(ids)
                    )
                )
            ).all()
        )
    services = []
    for row in rows:
        freshness = (
            "NO_DATA"
            if row.last_checked_at is None
            else "STALE"
            if (timestamp - row.last_checked_at).total_seconds()
            > row.interval_seconds * 2 + row.timeout_seconds
            else "FRESH"
        )
        services.append(
            {
                "id": str(row.id),
                "name": row.public_name,
                "state": row.state,
                "last_checked_at": row.last_checked_at,
                "freshness": freshness,
                "maintenance": row.internal_id in maintained,
                "show_history": row.show_history,
            }
        )
    active_services = [s for s in services if s["state"] != "PAUSED"]
    states = [s["state"] for s in active_services]
    overall = (
        "NO_DATA"
        if not services
        else "PAUSED"
        if not states
        else "DOWN"
        if "DOWN" in states
        else "UNKNOWN"
        if "UNKNOWN" in states or any(s["freshness"] != "FRESH" for s in active_services)
        else "UP"
    )
    return {"title": page.title, "state": overall, "services": services}


@app.get("/api/public/pages/{slug}")
async def public_page(slug: str):
    async with Session() as db:
        await readonly(db)
        return await snapshot(db, slug)


@app.get("/api/public/pages/{slug}/services/{identity}/analytics")
async def public_analytics(slug: str, identity: uuid.UUID, period: Period = "24h"):
    async with Session() as db:
        await readonly(db)
        monitor_id = await db.scalar(
            select(Publication.monitor_id)
            .join(PublicPage)
            .where(
                PublicPage.slug == slug,
                PublicPage.enabled,
                Publication.id == identity,
                Publication.show_history,
            )
        )
        if monitor_id is None:
            raise HTTPException(404, "Published history not found")
        return await aggregate(db, monitor_id, period)


async def public_events(slug, request):
    while not await request.is_disconnected():
        try:
            async with Session() as db:
                await readonly(db)
                data = await snapshot(db, slug)
        except HTTPException:
            yield "event: unavailable\ndata: {}\n\n"
            return
        except Exception:
            # Remove stale displayed data; reconnect performs a fresh authorization check.
            yield "event: unavailable\ndata: {}\n\n"
            return
        yield f"event: status\ndata: {json.dumps(jsonable_encoder(data))}\n\n"
        await asyncio.sleep(POLL_SECONDS)


@app.get("/api/public/pages/{slug}/events")
async def events(slug: str, request: Request):
    async with Session() as db:
        await readonly(db)
        await snapshot(db, slug)  # Disabled/unknown slugs return the same 404 before SSE starts.
    return StreamingResponse(
        public_events(slug, request),
        media_type="text/event-stream",
        headers={"X-Accel-Buffering": "no", "Cache-Control": "no-store"},
    )
