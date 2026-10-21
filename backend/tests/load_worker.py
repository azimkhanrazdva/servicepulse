"""Measurement wrapper around the real worker, used only by the isolated performance harness."""

import asyncio
import json
import time

from app import worker
from app.models import now

active = 0
real_check = worker.check


async def measured_check(monitor, client):
    global active
    active += 1
    started = time.perf_counter()
    print(
        json.dumps(
            {
                "measurement": "http_start",
                "monitor_id": str(monitor.id),
                "at": now().isoformat(),
                "due_at": monitor.next_due_at.isoformat(),
                "active": active,
            }
        ),
        flush=True,
    )
    outcome = "cancelled"
    try:
        result = await real_check(monitor, client)
        outcome = "success" if result.success else result.error
        return result
    finally:
        active -= 1
        print(
            json.dumps(
                {
                    "measurement": "http_end",
                    "monitor_id": str(monitor.id),
                    "at": now().isoformat(),
                    "seconds": time.perf_counter() - started,
                    "outcome": outcome,
                    "active": active,
                }
            ),
            flush=True,
        )


if __name__ == "__main__":
    worker.check = measured_check
    asyncio.run(worker.run())
