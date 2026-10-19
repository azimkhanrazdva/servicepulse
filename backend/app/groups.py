import uuid
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db import session_dependency
from app.models import Group, GroupRecipient, Monitor, MonitorGroup
from app.schemas import GroupCreate, GroupRead, GroupUpdate

router = APIRouter(prefix="/api/groups", tags=["groups"])
DB = Annotated[AsyncSession, Depends(session_dependency)]


def group_state(states):
    active = [state for state in states if state != "PAUSED"]
    if not states:
        return "UNKNOWN"
    if not active:
        return "PAUSED"
    return "DOWN" if "DOWN" in active else "UNKNOWN" if "UNKNOWN" in active else "UP"


async def group_snapshots(db, group_id=None):
    query = select(Group).order_by(Group.name, Group.id).limit(500)
    if group_id:
        query = query.where(Group.id == group_id)
    groups = (await db.scalars(query)).all()
    ids = [group.id for group in groups]
    members = (
        await db.execute(
            select(MonitorGroup.group_id, Monitor.id, Monitor.state)
            .join(Monitor, Monitor.id == MonitorGroup.monitor_id)
            .where(MonitorGroup.group_id.in_(ids))
            .order_by(Monitor.id)
        )
    ).all()
    recipients = (
        (
            await db.execute(
                select(GroupRecipient)
                .where(GroupRecipient.group_id.in_(ids))
                .order_by(GroupRecipient.email)
            )
        )
        .scalars()
        .all()
    )
    return [
        GroupRead(
            id=group.id,
            name=group.name,
            config_version=group.config_version,
            monitor_ids=[row.id for row in members if row.group_id == group.id],
            state=group_state([row.state for row in members if row.group_id == group.id]),
            recipients=[row.email for row in recipients if row.group_id == group.id],
        )
        for group in groups
    ]


async def find_group(db, group_id):
    group = await db.scalar(select(Group).where(Group.id == group_id).with_for_update())
    if group is None:
        raise HTTPException(404, "Group not found")
    return group


def require_version(current, version):
    if current.config_version != version:
        raise HTTPException(
            409, "Configuration changed in another client. Reload the editor and retry."
        )


async def replace_members_and_recipients(db, group, payload):
    # Group lock first, then monitor locks in UUID order; edits use the same order.
    members = (
        await db.scalars(
            select(Monitor.id)
            .where(Monitor.id.in_(payload.monitor_ids))
            .order_by(Monitor.id)
            .with_for_update()
        )
    ).all()
    if len(members) != len(payload.monitor_ids):
        raise HTTPException(422, "One or more selected monitors no longer exist")
    await db.execute(delete(MonitorGroup).where(MonitorGroup.group_id == group.id))
    await db.execute(delete(GroupRecipient).where(GroupRecipient.group_id == group.id))
    db.add_all([MonitorGroup(group_id=group.id, monitor_id=mid) for mid in members])
    db.add_all(
        [GroupRecipient(group_id=group.id, email=str(email)) for email in payload.recipients]
    )


@router.get("", response_model=list[GroupRead])
async def groups(db: DB):
    return await group_snapshots(db)


@router.post("", response_model=GroupRead, status_code=201)
async def create(payload: GroupCreate, db: DB):
    group = Group(name=payload.name)
    db.add(group)
    await db.flush()
    await replace_members_and_recipients(db, group, payload)
    await db.flush()
    snapshot = (await group_snapshots(db, group.id))[0]
    await db.commit()
    return snapshot


@router.get("/{group_id}", response_model=GroupRead)
async def detail(group_id: uuid.UUID, db: DB):
    snapshots = await group_snapshots(db, group_id)
    if not snapshots:
        raise HTTPException(404, "Group not found")
    return snapshots[0]


@router.put("/{group_id}", response_model=GroupRead)
async def update(group_id: uuid.UUID, payload: GroupUpdate, db: DB):
    group = await find_group(db, group_id)
    require_version(group, payload.config_version)
    await replace_members_and_recipients(db, group, payload)
    group.name = payload.name
    group.config_version += 1
    await db.flush()
    snapshot = (await group_snapshots(db, group.id))[0]
    await db.commit()
    return snapshot


@router.delete("/{group_id}", status_code=204)
async def remove(group_id: uuid.UUID, db: DB, config_version: Annotated[int, Query(ge=1)]):
    group = await find_group(db, group_id)
    require_version(group, config_version)
    await db.delete(group)
    await db.commit()
