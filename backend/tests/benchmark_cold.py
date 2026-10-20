"""One 100k-monitor-history fixture; separate-process/postgres-restart measurements."""

import asyncio
import json
import sys
import time
import uuid
from datetime import timedelta

from sqlalchemy import DateTime, Integer, bindparam, event, select, text

from app.analytics import BUCKET_SQL, aggregate
from app.db import Session, engine
from app.models import Monitor, now


async def main():
    assert engine.url.database == "servicepulse_test"
    if sys.argv[1] == "prepare":
        async with Session() as db, db.begin():
            assert await db.scalar(select(Monitor.id).limit(1)) is None
            monitor = Monitor(name="cold benchmark", url="http://example.com", state="PAUSED")
            db.add(monitor)
            await db.flush()
            mid = monitor.id
            await db.execute(
                text("""
              INSERT INTO check_results
                (id,monitor_id,checked_at,success,status_code,response_ms,config_version,interval_seconds)
              SELECT gen_random_uuid(),:mid,now()-interval '29 days'+i*interval '25 seconds',
                     i%10!=0,200,20,1,30 FROM generate_series(1,100000)i
            """),
                {"mid": mid},
            )
            await db.execute(text("ANALYZE check_results"))
        print(str(mid))
    elif sys.argv[1] == "plan":
        end = now()
        statement = text("EXPLAIN (ANALYZE, BUFFERS, FORMAT JSON) " + BUCKET_SQL.text).bindparams(
            bindparam("start", type_=DateTime(timezone=True)),
            bindparam("end", type_=DateTime(timezone=True)),
            bindparam("width", type_=Integer),
            bindparam("buckets", type_=Integer),
        )
        async with Session() as db:
            await db.execute(text("SET LOCAL jit = off"))
            plan = await db.scalar(
                statement,
                {
                    "mid": uuid.UUID(sys.argv[2]),
                    "start": end - timedelta(days=30),
                    "end": end,
                    "width": 7200,
                    "buckets": 360,
                },
            )
        print(json.dumps(plan))
    else:
        mid = uuid.UUID(sys.argv[2])
        calls, durations = [], []

        def before(*args):
            calls.append(time.perf_counter())

        def after(*args):
            durations.append(time.perf_counter() - calls[-1])

        event.listen(engine.sync_engine, "before_cursor_execute", before)
        event.listen(engine.sync_engine, "after_cursor_execute", after)
        measurements = []
        for index in range(8):
            calls.clear()
            durations.clear()
            tick = time.perf_counter()
            async with Session() as db:
                data = await aggregate(db, mid, "30d")
            elapsed = time.perf_counter() - tick
            tick = time.perf_counter()
            raw = json.dumps(data, default=str)
            serialization = time.perf_counter() - tick
            assert len(calls) == 2 and data["samples"] == 100000 and len(data["buckets"]) == 360
            measurements.append(
                {
                    "index": index,
                    "aggregate_seconds": elapsed,
                    "sql_driver_seconds": sum(durations),
                    "non_sql_seconds": elapsed - sum(durations),
                    "serialization_seconds": serialization,
                    "query_count": len(calls),
                    "aggregate_query_count": 1,
                    "transaction_local_setting_count": 1,
                    "bytes": len(raw.encode()),
                    "buckets": 360,
                }
            )
        print(json.dumps({"at": now().isoformat(), "measurements": measurements}))
    await engine.dispose()


if __name__ == "__main__":
    asyncio.run(main())
