import asyncio
import contextlib
import json
import logging
import signal
import uuid
from datetime import timedelta

import httpx
from sqlalchemy import or_, select

from app.checker import check, transition
from app.config import settings
from app.db import Session, engine
from app.incidents import observe_incident
from app.models import CheckResult, Monitor, now

log = logging.getLogger("servicepulse.worker")


async def claim_due(limit):
    if limit <= 0:
        return []
    async with Session() as db, db.begin():
        monitors = (
            await db.scalars(
                select(Monitor)
                .where(
                    Monitor.state != "PAUSED",
                    Monitor.next_due_at <= now(),
                    or_(Monitor.lease_until.is_(None), Monitor.lease_until <= now()),
                )
                .order_by(Monitor.next_due_at)
                .with_for_update(skip_locked=True)
                .limit(limit)
            )
        ).all()
        for monitor in monitors:
            monitor.lease_token = uuid.uuid4()
            monitor.lease_until = now() + timedelta(seconds=monitor.timeout_seconds + 15)
            monitor.run_requested = False
        return monitors


async def execute(monitor, client):
    async with Session() as db, db.begin():
        current = await db.scalar(select(Monitor).where(Monitor.id == monitor.id).with_for_update())
        if current is None or current.lease_token != monitor.lease_token:
            return
        if current.config_version != monitor.config_version or current.state == "PAUSED":
            current.lease_token = current.lease_until = None
            return
    observation = await check(monitor, client)
    observed_at = now()  # HTTP completion, before waiting for the persistence row lock.
    async with Session() as db, db.begin():
        current = await db.scalar(select(Monitor).where(Monitor.id == monitor.id).with_for_update())
        if current is None or current.lease_token != monitor.lease_token:
            return
        if current.config_version != monitor.config_version or current.state == "PAUSED":
            current.lease_token = current.lease_until = None
            return
        current.state, current.consecutive_failures = transition(
            current.state,
            current.consecutive_failures,
            observation.success,
            current.failure_threshold,
        )
        current.last_checked_at = observed_at
        await observe_incident(db, current, observation.success, observed_at)
        current.last_status_code = observation.status_code
        current.last_response_ms = observation.response_ms
        current.next_due_at = (
            now() if current.run_requested else now() + timedelta(seconds=current.interval_seconds)
        )
        current.lease_token = current.lease_until = None
        db.add(
            CheckResult(
                monitor_id=current.id,
                checked_at=current.last_checked_at,
                success=observation.success,
                status_code=observation.status_code,
                response_ms=observation.response_ms,
                error=observation.error,
                config_version=monitor.config_version,
                interval_seconds=monitor.interval_seconds,
            )
        )
    log.info(
        json.dumps(
            {
                "event": "check_completed",
                "monitor_id": str(monitor.id),
                "success": observation.success,
                "response_ms": observation.response_ms,
            }
        )
    )


async def run():
    stop = asyncio.Event()
    loop = asyncio.get_running_loop()
    for sig in (signal.SIGINT, signal.SIGTERM):
        with contextlib.suppress(NotImplementedError):
            loop.add_signal_handler(sig, stop.set)
    tasks = set()
    async with httpx.AsyncClient(
        trust_env=False,
        follow_redirects=False,
        limits=httpx.Limits(max_connections=settings.concurrency, max_keepalive_connections=20),
    ) as client:
        try:
            while not stop.is_set():
                for task in list(tasks):
                    if task.done():
                        tasks.remove(task)
                        if not task.cancelled() and task.exception():
                            log.error(
                                json.dumps(
                                    {
                                        "event": "task_failed",
                                        "type": type(task.exception()).__name__,
                                    }
                                )
                            )
                try:
                    for monitor in await claim_due(settings.concurrency - len(tasks)):
                        tasks.add(asyncio.create_task(execute(monitor, client)))
                except Exception as exc:
                    log.error(json.dumps({"event": "scheduler_error", "type": type(exc).__name__}))
                with contextlib.suppress(TimeoutError):
                    await asyncio.wait_for(stop.wait(), timeout=0.5)
        finally:
            for task in tasks:
                task.cancel()
            await asyncio.gather(*tasks, return_exceptions=True)
            await engine.dispose()


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format="%(message)s")
    asyncio.run(run())
