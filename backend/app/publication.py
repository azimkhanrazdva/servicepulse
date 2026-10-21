"""Management-only publication configuration, independent of monitoring configuration."""

import uuid
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.db import session_dependency
from app.groups import require_version
from app.models import Monitor, Publication, PublicPage
from app.schemas import VersionRequest

router = APIRouter(prefix="/api/status-pages", tags=["publication management"])
DB = Annotated[AsyncSession, Depends(session_dependency)]


class PublishInput(BaseModel):
    model_config = ConfigDict(extra="forbid")
    monitor_id: uuid.UUID
    public_name: str = Field(min_length=1, max_length=120)
    show_history: bool = False

    @field_validator("public_name", mode="before")
    @classmethod
    def strip_name(cls, value):
        return value.strip() if isinstance(value, str) else value


class PageInput(BaseModel):
    model_config = ConfigDict(extra="forbid")
    slug: str = Field(min_length=3, max_length=64, pattern=r"^[a-z0-9][a-z0-9-]+[a-z0-9]$")
    title: str = Field(min_length=1, max_length=120)
    enabled: bool = False
    publications: list[PublishInput] = Field(default_factory=list, max_length=500)

    @field_validator("title", mode="before")
    @classmethod
    def strip_title(cls, value):
        return value.strip() if isinstance(value, str) else value

    @model_validator(mode="after")
    def distinct(self):
        ids = [p.monitor_id for p in self.publications]
        if len(ids) != len(set(ids)):
            raise ValueError("Each monitor can appear once per page")
        return self


class PageUpdate(PageInput, VersionRequest):
    pass


async def read_page(db, page):
    publications = (
        await db.scalars(
            select(Publication).where(Publication.page_id == page.id).order_by(Publication.id)
        )
    ).all()
    return {
        "id": page.id,
        "slug": page.slug,
        "title": page.title,
        "enabled": page.enabled,
        "config_version": page.config_version,
        "publications": [
            {
                "id": p.id,
                "monitor_id": p.monitor_id,
                "public_name": p.public_name,
                "show_history": p.show_history,
            }
            for p in publications
        ],
    }


async def replace_publications(db, page, values):
    ids = [p.monitor_id for p in values]
    existing_ids = (
        await db.scalars(
            select(Monitor.id).where(Monitor.id.in_(ids)).order_by(Monitor.id).with_for_update()
        )
    ).all()
    if len(existing_ids) != len(ids):
        raise HTTPException(422, "One or more selected monitors no longer exist")
    previous = {
        p.monitor_id: p
        for p in (await db.scalars(select(Publication).where(Publication.page_id == page.id))).all()
    }
    for mid, publication in previous.items():
        if mid not in ids:
            await db.delete(publication)
    for value in values:
        publication = previous.get(value.monitor_id)
        if publication is None:
            publication = Publication(page_id=page.id, monitor_id=value.monitor_id)
            db.add(publication)
        publication.public_name = value.public_name
        publication.show_history = value.show_history


async def commit_page(db, page):
    try:
        await db.flush()
        response = await read_page(db, page)
        await db.commit()
        return response
    except IntegrityError as exc:
        await db.rollback()
        raise HTTPException(409, "Page slug is already in use") from exc


@router.get("")
async def pages(db: DB):
    rows = (await db.scalars(select(PublicPage).order_by(PublicPage.slug).limit(100))).all()
    return [await read_page(db, page) for page in rows]


@router.post("", status_code=201)
async def create_page(payload: PageInput, db: DB):
    page = PublicPage(slug=payload.slug, title=payload.title, enabled=payload.enabled)
    db.add(page)
    # UUID is needed before publication FK insertion; catch duplicate slugs here as well.
    try:
        await db.flush()
    except IntegrityError as exc:
        raise HTTPException(409, "Page slug is already in use") from exc
    await replace_publications(db, page, payload.publications)
    return await commit_page(db, page)


@router.put("/{identity}")
async def update_page(identity: uuid.UUID, payload: PageUpdate, db: DB):
    page = await db.scalar(select(PublicPage).where(PublicPage.id == identity).with_for_update())
    if page is None:
        raise HTTPException(404, "Status page not found")
    require_version(page, payload.config_version)
    page.slug, page.title, page.enabled = payload.slug, payload.title, payload.enabled
    page.config_version += 1
    await replace_publications(db, page, payload.publications)
    return await commit_page(db, page)


@router.delete("/{identity}", status_code=204)
async def delete_page(identity: uuid.UUID, config_version: Annotated[int, Query(ge=1)], db: DB):
    page = await db.scalar(select(PublicPage).where(PublicPage.id == identity).with_for_update())
    if page is None:
        raise HTTPException(404, "Status page not found")
    require_version(page, config_version)
    await db.delete(page)
    await db.commit()
