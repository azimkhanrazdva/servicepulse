import uuid
from datetime import datetime
from typing import Annotated, Literal

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db import session_dependency
from app.groups import require_version
from app.models import Group, MaintenanceWindow, Monitor, MonitorGroup, now
from app.schemas import VersionRequest

router = APIRouter(prefix="/api/maintenance", tags=["maintenance"])
DB = Annotated[AsyncSession, Depends(session_dependency)]


class WindowCreate(BaseModel):
    model_config = ConfigDict(extra="forbid")
    name: str = Field(min_length=1, max_length=120)
    monitor_id: uuid.UUID | None = None
    group_id: uuid.UUID | None = None
    start_at: datetime
    end_at: datetime

    @field_validator("name")
    @classmethod
    def trim_name(cls, value):
        if not value.strip():
            raise ValueError("Name is required")
        return value.strip()

    @model_validator(mode="after")
    def valid_window(self):
        if (self.monitor_id is None) == (self.group_id is None):
            raise ValueError("Choose exactly one monitor or group")
        if self.start_at.utcoffset() is None or self.end_at.utcoffset() is None:
            raise ValueError("Dates require an explicit timezone")
        if self.end_at <= self.start_at:
            raise ValueError("End must be later than start")
        return self


class WindowUpdate(WindowCreate, VersionRequest):
    pass


class WindowRead(WindowCreate):
    model_config = ConfigDict(from_attributes=True)
    id: uuid.UUID
    config_version: int
    created_at: datetime
    state: str


def window_state(window, timestamp):
    return (
        "UPCOMING"
        if timestamp < window.start_at
        else "ACTIVE"
        if timestamp < window.end_at
        else "ENDED"
    )


def window_read(window, timestamp):
    return WindowRead(
        **{
            key: getattr(window, key)
            for key in (
                "id",
                "name",
                "monitor_id",
                "group_id",
                "start_at",
                "end_at",
                "created_at",
                "config_version",
            )
        },
        state=window_state(window, timestamp),
    )


async def window_snapshot(db, state=None, limit=100, offset=0):
    timestamp = now()
    stmt = select(MaintenanceWindow)
    if state == "ACTIVE":
        stmt = stmt.where(
            MaintenanceWindow.start_at <= timestamp, MaintenanceWindow.end_at > timestamp
        )
    elif state == "UPCOMING":
        stmt = stmt.where(MaintenanceWindow.start_at > timestamp)
    elif state == "ENDED":
        stmt = stmt.where(MaintenanceWindow.end_at <= timestamp)
    rows = (
        await db.scalars(
            stmt.order_by(MaintenanceWindow.start_at.desc(), MaintenanceWindow.id)
            .offset(offset)
            .limit(limit + 1)
        )
    ).all()
    active = (
        await db.execute(
            select(MaintenanceWindow.monitor_id, MaintenanceWindow.group_id).where(
                MaintenanceWindow.start_at <= timestamp, MaintenanceWindow.end_at > timestamp
            )
        )
    ).all()
    active_monitors = {r.monitor_id for r in active if r.monitor_id}
    active_groups = {r.group_id for r in active if r.group_id}
    active_monitors.update(
        (
            await db.scalars(
                select(MonitorGroup.monitor_id).where(MonitorGroup.group_id.in_(active_groups))
            )
        ).all()
    )
    return {
        "items": [window_read(w, timestamp).model_dump(mode="json") for w in rows[:limit]],
        "has_more": len(rows) > limit,
        "limit": limit,
        "offset": offset,
        "active_monitor_ids": sorted(str(x) for x in active_monitors),
        "active_group_ids": sorted(str(x) for x in active_groups),
    }


async def validate_target(db, payload):
    model, identity = (
        (Monitor, payload.monitor_id) if payload.monitor_id else (Group, payload.group_id)
    )
    if await db.scalar(select(model.id).where(model.id == identity).with_for_update()) is None:
        raise HTTPException(404, "Maintenance target not found")


@router.get("")
async def windows(
    db: DB,
    state: Literal["ACTIVE", "UPCOMING", "ENDED"] | None = None,
    limit: Annotated[int, Query(ge=1, le=100)] = 100,
    offset: Annotated[int, Query(ge=0, le=10000)] = 0,
):
    return await window_snapshot(db, state, limit, offset)


@router.post("", response_model=WindowRead, status_code=201)
async def create_window(payload: WindowCreate, db: DB):
    await validate_target(db, payload)
    window = MaintenanceWindow(**payload.model_dump())
    db.add(window)
    await db.flush()
    response = window_read(window, now())
    await db.commit()
    return response


async def find_window(db, identity, version):
    window = await db.scalar(
        select(MaintenanceWindow)
        .where(MaintenanceWindow.id == identity)
        .with_for_update()
        .execution_options(populate_existing=True)
    )
    if window is None:
        raise HTTPException(404, "Maintenance window not found")
    require_version(window, version)
    return window


@router.put("/{identity}", response_model=WindowRead)
async def update_window(identity: uuid.UUID, payload: WindowUpdate, db: DB):
    previous = await db.get(MaintenanceWindow, identity)
    if previous is None:
        raise HTTPException(404, "Maintenance window not found")
    # Parent locks before window: parent DELETE cascades to windows. Group before monitor
    # matches existing group membership edits, with UUID ordering within each kind.
    for model, ids in (
        (Group, {previous.group_id, payload.group_id}),
        (Monitor, {previous.monitor_id, payload.monitor_id}),
    ):
        for target in sorted(x for x in ids if x is not None):
            if (
                await db.scalar(select(model.id).where(model.id == target).with_for_update())
                is None
            ):
                raise HTTPException(404, "Maintenance target not found")
    # Refresh the cached row under lock, so concurrent edits cannot pass a stale version.
    await db.refresh(previous)
    window = await find_window(db, identity, payload.config_version)
    for key, value in payload.model_dump(exclude={"config_version"}).items():
        setattr(window, key, value)
    window.config_version += 1
    await db.flush()
    response = window_read(window, now())
    await db.commit()
    return response


@router.delete("/{identity}", status_code=204)
async def delete_window(identity: uuid.UUID, db: DB, config_version: Annotated[int, Query(ge=1)]):
    await db.delete(await find_window(db, identity, config_version))
    await db.commit()
