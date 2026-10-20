"""Bounded PostgreSQL aggregates; no raw month of ORM observations is materialized."""

import uuid
from datetime import timedelta
from typing import Annotated, Literal

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import DateTime, Integer, bindparam, select, text
from sqlalchemy.ext.asyncio import AsyncSession

from app.db import session_dependency
from app.models import Monitor, now

router = APIRouter(tags=["analytics"])
Period = Literal["24h", "7d", "30d"]
PERIODS = {"24h": (86400, 300), "7d": (604800, 1800), "30d": (2592000, 7200)}

BUCKET_SQL = text("""
WITH observations AS (
    SELECT checked_at, success, response_ms, interval_seconds,
           lead(checked_at) OVER (ORDER BY checked_at,id) AS next_at
    FROM check_results
    WHERE monitor_id=:mid AND checked_at >= :start - interval '1 hour' AND checked_at < :end
), samples AS (
    SELECT floor(extract(epoch FROM (checked_at - :start)) / :width)::int AS idx,
           count(*) AS samples, count(*) FILTER (WHERE success) AS successful,
           avg(response_ms) AS mean_ms, min(response_ms) AS min_ms, max(response_ms) AS max_ms
    FROM observations WHERE checked_at >= :start GROUP BY 1
), spans AS (
    SELECT greatest(checked_at,:start) AS lo,
           least(coalesce(next_at,:end),
                 checked_at + interval_seconds * interval '1 second',:end) AS hi
    FROM observations WHERE interval_seconds IS NOT NULL
), coverage AS (
    SELECT g.idx, sum(extract(epoch FROM (
        least(hi,:start + (g.idx+1)*:width*interval '1 second') -
        greatest(lo,:start + g.idx*:width*interval '1 second')
    ))) AS covered_seconds
    FROM spans CROSS JOIN LATERAL generate_series(
        greatest(0,floor(extract(epoch FROM (lo-:start))/:width)::int),
        least(:buckets-1,floor((extract(epoch FROM (hi-:start))-0.000001)/:width)::int)
    ) AS g(idx) WHERE hi > lo GROUP BY g.idx
)
SELECT g.idx, coalesce(s.samples,0) AS samples, coalesce(s.successful,0) AS successful,
       s.mean_ms,s.min_ms,s.max_ms,coalesce(c.covered_seconds,0) AS covered_seconds
FROM generate_series(0,:buckets-1) AS g(idx)
LEFT JOIN samples s USING(idx) LEFT JOIN coverage c USING(idx) ORDER BY g.idx
""").bindparams(
    bindparam("start", type_=DateTime(timezone=True)),
    bindparam("end", type_=DateTime(timezone=True)),
    bindparam("width", type_=Integer),
    bindparam("buckets", type_=Integer),
)


async def aggregate(db, monitor_id, period, timestamp=None):
    end = timestamp or now()
    seconds, width = PERIODS[period]
    start = end - timedelta(seconds=seconds)
    # The dense-history plan spends more time compiling JIT than executing useful work.
    # Keep this transaction-local; do not change PostgreSQL or connection defaults.
    await db.execute(text("SET LOCAL jit = off"))
    rows = (
        (
            await db.execute(
                BUCKET_SQL,
                {
                    "mid": monitor_id,
                    "start": start,
                    "end": end,
                    "width": width,
                    "buckets": seconds // width,
                },
            )
        )
        .mappings()
        .all()
    )
    samples = sum(r["samples"] for r in rows)
    successful = sum(r["successful"] for r in rows)
    covered = float(sum(r["covered_seconds"] for r in rows))
    return {
        "period": period,
        "start_at": start,
        "end_at": end,
        "bucket_seconds": width,
        "samples": samples,
        "successful": successful,
        "uptime_percent": successful * 100 / samples if samples else None,
        "coverage_percent": min(100, covered * 100 / seconds),
        "unobserved_seconds": max(0, seconds - covered),
        "status": "OBSERVED" if samples else "NO_DATA",
        "buckets": [
            {
                "at": start + timedelta(seconds=r["idx"] * width),
                "samples": r["samples"],
                "successful": r["successful"],
                "mean_ms": float(r["mean_ms"]) if r["mean_ms"] is not None else None,
                "min_ms": r["min_ms"],
                "max_ms": r["max_ms"],
                "coverage_percent": min(100, float(r["covered_seconds"]) * 100 / width),
            }
            for r in rows
        ],
    }


@router.get("/api/monitors/{monitor_id}/analytics")
async def analytics(
    monitor_id: uuid.UUID,
    db: Annotated[AsyncSession, Depends(session_dependency)],
    period: Period = "24h",
):
    if await db.scalar(select(Monitor.id).where(Monitor.id == monitor_id)) is None:
        raise HTTPException(404, "Monitor not found")
    return await aggregate(db, monitor_id, period)
