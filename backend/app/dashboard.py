"""Cheap live incident summaries; sample aggregates are polled separately from SSE."""

from datetime import timedelta
from typing import Annotated

from fastapi import APIRouter, Depends
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db import session_dependency
from app.models import CheckResult, Incident, Monitor, now

router = APIRouter(tags=["dashboard"])


async def live_overview(db):
    visible = select(Monitor.id).order_by(Monitor.created_at).limit(500)
    opened = (
        await db.execute(
            select(Incident.monitor_id, Incident.opened_at).where(
                Incident.closed_at.is_(None), Incident.monitor_id.in_(visible)
            )
        )
    ).all()
    active = await db.scalar(
        select(func.count()).select_from(Incident).where(Incident.closed_at.is_(None))
    )
    return {
        "active_incidents": active,
        "opened_at": {str(r.monitor_id): r.opened_at for r in opened},
    }


@router.get("/api/overview")
async def overview(db: Annotated[AsyncSession, Depends(session_dependency)]):
    await db.connection(execution_options={"isolation_level": "REPEATABLE READ"})
    timestamp = now()
    visible = select(Monitor.id).order_by(Monitor.created_at).limit(500)
    rows = (
        await db.execute(
            select(
                CheckResult.monitor_id,
                func.count().label("samples"),
                func.count().filter(CheckResult.success).label("successful"),
            )
            .where(
                CheckResult.monitor_id.in_(visible),
                CheckResult.checked_at >= timestamp - timedelta(days=1),
                CheckResult.checked_at < timestamp,
            )
            .group_by(CheckResult.monitor_id)
        )
    ).all()
    return {
        **await live_overview(db),
        "uptime_24h": {
            str(row.monitor_id): {
                "samples": row.samples,
                "percent": row.successful * 100 / row.samples,
            }
            for row in rows
        },
    }
