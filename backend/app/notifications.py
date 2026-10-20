"""Durable logical events, frozen routes, and per-address delivery scheduling."""

import uuid
from datetime import timedelta
from typing import Annotated

from fastapi import APIRouter, Depends, Query
from sqlalchemy import and_, func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db import Session, session_dependency
from app.models import (
    GroupRecipient,
    Incident,
    MaintenanceWindow,
    Monitor,
    MonitorGroup,
    NotificationDelivery,
    NotificationEvent,
    NotificationRoute,
    now,
)

router = APIRouter(tags=["notifications"])
POLL_SECONDS = 2
MAX_ATTEMPTS = 8


async def create_event(db, incident, monitor_name, event_type):
    """Caller holds monitor lock; event/routes/deliveries join its existing transaction."""
    if not incident.notifications_enabled:
        return
    if await db.scalar(
        select(NotificationEvent.id).where(
            NotificationEvent.incident_id == incident.id, NotificationEvent.event_type == event_type
        )
    ):
        return
    if event_type == "DOWN":
        routes = (
            await db.execute(
                select(MonitorGroup.group_id, func.lower(GroupRecipient.email))
                .join(GroupRecipient, MonitorGroup.group_id == GroupRecipient.group_id)
                .where(MonitorGroup.monitor_id == incident.monitor_id)
            )
        ).all()
    else:
        routes = (
            await db.execute(
                select(NotificationRoute.group_id, NotificationRoute.email)
                .join(NotificationEvent)
                .where(
                    NotificationEvent.incident_id == incident.id,
                    NotificationEvent.event_type == "DOWN",
                )
            )
        ).all()
    event = NotificationEvent(
        id=uuid.uuid4(), incident_id=incident.id, event_type=event_type, monitor_name=monitor_name
    )
    db.add(event)
    await db.flush()
    distinct = set(routes)
    db.add_all(
        [NotificationRoute(event_id=event.id, group_id=gid, email=email) for gid, email in distinct]
    )
    db.add_all(
        [
            NotificationDelivery(event_id=event.id, email=email, next_attempt_at=now())
            for email in {r[1] for r in distinct}
        ]
    )


async def applicable_routes(db, event_id, monitor_id, email, timestamp):
    """Return (still configured, allowed now). An eligible group can release a shared address."""
    group_ids = (
        await db.scalars(
            select(NotificationRoute.group_id)
            .join(
                MonitorGroup,
                and_(
                    MonitorGroup.group_id == NotificationRoute.group_id,
                    MonitorGroup.monitor_id == monitor_id,
                ),
            )
            .join(
                GroupRecipient,
                and_(
                    GroupRecipient.group_id == NotificationRoute.group_id,
                    func.lower(GroupRecipient.email) == NotificationRoute.email,
                ),
            )
            .where(NotificationRoute.event_id == event_id, NotificationRoute.email == email)
        )
    ).all()
    if not group_ids:
        return False, False
    windows = (
        await db.scalars(
            select(MaintenanceWindow).where(
                MaintenanceWindow.start_at <= timestamp,
                MaintenanceWindow.end_at > timestamp,
                or_(
                    MaintenanceWindow.monitor_id == monitor_id,
                    MaintenanceWindow.group_id.in_(group_ids),
                ),
            )
        )
    ).all()
    if any(w.monitor_id == monitor_id for w in windows):
        return True, False
    suppressed = {w.group_id for w in windows}
    return True, any(gid not in suppressed for gid in group_ids)


async def claim_deliveries(limit=10, lease_seconds=130):
    if limit <= 0:
        return []
    timestamp = now()
    async with Session() as db, db.begin():
        rows = (
            await db.scalars(
                select(NotificationDelivery)
                .where(
                    or_(
                        and_(
                            NotificationDelivery.status == "PENDING",
                            NotificationDelivery.next_attempt_at <= timestamp,
                        ),
                        and_(
                            NotificationDelivery.status == "INFLIGHT",
                            NotificationDelivery.lease_until <= timestamp,
                        ),
                    )
                )
                .order_by(NotificationDelivery.next_attempt_at, NotificationDelivery.id)
                .with_for_update(skip_locked=True)
                .limit(limit)
            )
        ).all()
        for row in rows:
            row.status = "INFLIGHT"
            row.lease_token = uuid.uuid4()
            row.lease_until = timestamp + timedelta(seconds=lease_seconds)
        return rows


def release(row, status, timestamp, delay=0):
    row.status = status
    row.lease_token = row.lease_until = None
    row.next_attempt_at = timestamp + timedelta(seconds=delay)


async def prepare(claim, authorize=True):
    """Last persisted authorization before SMTP; no transaction remains open during network I/O."""
    async with Session() as db, db.begin():
        parent = (
            await db.execute(
                select(NotificationEvent, Incident)
                .join(Incident)
                .where(NotificationEvent.id == claim.event_id)
            )
        ).one_or_none()
        if parent is None:
            return None
        event, incident = parent
        monitor = await db.scalar(
            select(Monitor).where(Monitor.id == incident.monitor_id).with_for_update()
        )
        row = await db.scalar(
            select(NotificationDelivery)
            .where(NotificationDelivery.id == claim.id)
            .with_for_update()
        )
        timestamp = now()
        if (
            monitor is None
            or row is None
            or row.lease_token != claim.lease_token
            or row.lease_until <= timestamp
        ):
            return None
        # Refresh incident after waiting for the monitor lock (READ COMMITTED statement snapshot).
        await db.refresh(incident)
        if event.event_type == "DOWN":
            if incident.closed_at and (
                incident.closure_reason != "RECOVERED" or row.send_started_at is None
            ):
                release(row, "CANCELLED", timestamp)
                return None
        else:
            down = await db.scalar(
                select(NotificationDelivery)
                .join(NotificationEvent)
                .where(
                    NotificationEvent.incident_id == incident.id,
                    NotificationEvent.event_type == "DOWN",
                    NotificationDelivery.email == row.email,
                )
            )
            if down is None or down.status in {"CANCELLED", "FAILED"}:
                release(row, "CANCELLED", timestamp)
                return None
            if down.status != "SENT":
                release(row, "PENDING", timestamp, POLL_SECONDS)
                return None
        configured, allowed = await applicable_routes(
            db, event.id, monitor.id, row.email, timestamp
        )
        if not configured:
            release(row, "CANCELLED", timestamp)
            return None
        if not allowed:
            release(row, "PENDING", timestamp, POLL_SECONDS)
            return None
        if not authorize:
            release(row, "PENDING", timestamp)
            return None
        if row.attempts >= MAX_ATTEMPTS:
            release(row, "FAILED", timestamp)
            row.last_error = "retry_exhausted"
            return None
        row.attempts += 1
        row.send_started_at = timestamp
        return {
            "delivery_id": str(row.id),
            "incident_id": str(incident.id),
            "event_type": event.event_type,
            "email": row.email,
            "monitor_name": event.monitor_name,
            "opened_at": incident.opened_at.isoformat(),
            "recovered_at": incident.recovered_at.isoformat() if incident.recovered_at else None,
        }


async def reconcile():
    """Runs independently of HTTP results, including when windows end or incidents close."""
    for row in await claim_deliveries(100):
        await prepare(row, authorize=False)


async def acknowledge(claim, error=None, permanent=False, definite_rejection=False):
    async with Session() as db, db.begin():
        row = await db.scalar(
            select(NotificationDelivery)
            .where(NotificationDelivery.id == claim.id)
            .with_for_update()
        )
        if row is None or row.lease_token != claim.lease_token:
            return
        timestamp = now()
        if error is None:
            release(row, "SENT", timestamp)
            row.sent_at, row.last_error = timestamp, None
        else:
            release(
                row,
                "FAILED" if permanent or row.attempts >= MAX_ATTEMPTS else "PENDING",
                timestamp,
                min(300, 5 * 2 ** max(0, row.attempts - 1)),
            )
            row.last_error = error
            if definite_rejection:
                row.send_started_at = None


@router.get("/api/notifications")
async def delivery_status(
    db: Annotated[AsyncSession, Depends(session_dependency)],
    incident_id: uuid.UUID | None = None,
    limit: Annotated[int, Query(ge=1, le=100)] = 50,
    offset: Annotated[int, Query(ge=0, le=10000)] = 0,
):
    stmt = select(NotificationDelivery, NotificationEvent).join(NotificationEvent)
    if incident_id:
        stmt = stmt.where(NotificationEvent.incident_id == incident_id)
    rows = (
        await db.execute(
            stmt.order_by(NotificationDelivery.created_at.desc(), NotificationDelivery.id)
            .offset(offset)
            .limit(limit + 1)
        )
    ).all()
    return {
        "items": [
            {
                "id": d.id,
                "incident_id": e.incident_id,
                "event_type": e.event_type,
                "email": d.email,
                "status": d.status,
                "attempts": d.attempts,
                "next_attempt_at": d.next_attempt_at,
                "sent_at": d.sent_at,
                "last_error": d.last_error,
            }
            for d, e in rows[:limit]
        ],
        "has_more": len(rows) > limit,
    }
