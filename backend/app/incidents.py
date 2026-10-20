"""Incident queries and lifecycle; callers hold the monitor row lock for mutations."""

import uuid
from datetime import datetime
from typing import Annotated, Literal

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db import session_dependency
from app.models import Incident, Monitor, now
from app.schemas import IncidentPage, IncidentRead

router = APIRouter()
DB = Annotated[AsyncSession, Depends(session_dependency)]


async def close_incident(db, monitor_id, reason, at):
    incident = await db.scalar(
        select(Incident).where(Incident.monitor_id == monitor_id, Incident.closed_at.is_(None))
    )
    if incident is not None:
        incident.closed_at = max(at, incident.opened_at)
        incident.closure_reason = reason
        if reason == "RECOVERED":
            incident.recovered_at = incident.closed_at


async def observe_incident(db, monitor, success, observed_at):
    if success:
        await close_incident(db, monitor.id, "RECOVERED", observed_at)
    elif monitor.state == "DOWN":
        existing = await db.scalar(
            select(Incident.id).where(
                Incident.monitor_id == monitor.id, Incident.closed_at.is_(None)
            )
        )
        if existing is None:
            db.add(Incident(monitor_id=monitor.id, opened_at=observed_at))


async def incident_page(
    db, monitor_id=None, state=None, since=None, until=None, limit=50, offset=0, order="desc"
):
    if since and until and since > until:
        raise HTTPException(422, "since must not exceed until")
    stmt = select(Incident, Monitor.name).join(Monitor, Incident.monitor_id == Monitor.id)
    if monitor_id:
        stmt = stmt.where(Incident.monitor_id == monitor_id)
    if state:
        stmt = stmt.where(
            Incident.closed_at.is_(None) if state == "OPEN" else Incident.closed_at.is_not(None)
        )
    if since:
        stmt = stmt.where(Incident.opened_at >= since)
    if until:
        stmt = stmt.where(Incident.opened_at <= until)
    sort = (
        (Incident.opened_at.asc(), Incident.id.asc())
        if order == "asc"
        else (Incident.opened_at.desc(), Incident.id.desc())
    )
    rows = (await db.execute(stmt.order_by(*sort).offset(offset).limit(limit + 1))).all()
    timestamp = now()
    return IncidentPage(
        items=[IncidentRead.from_row(row, name, timestamp) for row, name in rows[:limit]],
        has_more=len(rows) > limit,
        limit=limit,
        offset=offset,
    )


@router.get("/api/incidents", response_model=IncidentPage)
@router.get("/api/monitors/{monitor_id}/incidents", response_model=IncidentPage)
async def list_incidents(
    db: DB,
    monitor_id: uuid.UUID | None = None,
    state: Literal["OPEN", "CLOSED"] | None = None,
    since: datetime | None = None,
    until: datetime | None = None,
    limit: Annotated[int, Query(ge=1, le=100)] = 50,
    offset: Annotated[int, Query(ge=0, le=10000)] = 0,
    order: Literal["asc", "desc"] = "desc",
):
    for value in (since, until):
        if value and value.utcoffset() is None:
            raise HTTPException(422, "Dates require an explicit timezone")
    if monitor_id and await db.get(Monitor, monitor_id) is None:
        raise HTTPException(404, "Monitor not found")
    return await incident_page(db, monitor_id, state, since, until, limit, offset, order)


@router.get("/api/incidents/active", response_model=IncidentPage)
async def active_incidents(
    db: DB,
    limit: Annotated[int, Query(ge=1, le=100)] = 50,
    offset: Annotated[int, Query(ge=0, le=10000)] = 0,
):
    return await incident_page(db, state="OPEN", limit=limit, offset=offset)


@router.get("/api/incidents/{incident_id}", response_model=IncidentRead)
async def incident_detail(incident_id: uuid.UUID, db: DB):
    row = (
        await db.execute(
            select(Incident, Monitor.name).join(Monitor).where(Incident.id == incident_id)
        )
    ).one_or_none()
    if row is None:
        raise HTTPException(404, "Incident not found")
    return IncidentRead.from_row(*row, now())
