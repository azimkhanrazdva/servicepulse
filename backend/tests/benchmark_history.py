"""Synthetic fleet history benchmark in the explicitly disposable performance DB."""

import asyncio
import json
import math
import os
import statistics
import time
import uuid
from datetime import timedelta
from pathlib import Path

from sqlalchemy import DateTime, Integer, bindparam, text

from app.analytics import BUCKET_SQL, aggregate
from app.db import Session, engine
from app.models import now


def quantiles(values):
    ordered = sorted(values)
    return {
        "runs": len(values),
        "mean_seconds": statistics.mean(values),
        **{
            f"p{percent}_seconds": ordered[math.ceil(len(values) * percent / 100) - 1]
            for percent in (50, 95, 99)
        },
        "max_seconds": max(values),
    }


async def main():
    assert engine.url.database == "servicepulse_test"
    assert os.environ.get("PERFORMANCE_BENCHMARK") == "isolated-synthetic-history"
    report = {
        "started_at": now().isoformat(),
        "synthetic": True,
        "distribution": "50 monitors, uniform synthetic observations across 30 days",
        "percentiles": "nearest rank; seven warm repetitions after first run",
        "datasets": [],
    }
    mid = uuid.uuid4()
    end = now()
    async with engine.begin() as db:
        await db.execute(
            text("""
            INSERT INTO monitors (id,name,url,interval_seconds,timeout_seconds,expected_status,
              failure_threshold,state,consecutive_failures,created_at,next_due_at,config_version,run_requested)
            VALUES (:mid,'synthetic benchmark','http://example.com',30,5,200,2,'PAUSED',0,now(),now(),1,false)
        """),
            {"mid": mid},
        )
    try:
        for total, fleet in ((10000, 50), (100000, 50), (500000, 50), (1000000, 50), (100000, 1)):
            # All rows belong to this fixture monitor; distribution encoded by 50 distinct UUIDs.
            # Keep real FKs by inserting 49 additional paused fixture monitors once.
            async with engine.begin() as db:
                if total == 10000:
                    for index in range(1, 50):
                        await db.execute(
                            text("""
                            INSERT INTO monitors SELECT (json_populate_record(NULL::monitors,
                              (to_jsonb(m) || jsonb_build_object('id',CAST(:id AS text),
                                'name',CAST(:name AS text)))::json)).*
                            FROM monitors m WHERE m.id=:mid
                        """),
                            {
                                "id": str(uuid.uuid4()),
                                "name": f"synthetic benchmark {index}",
                                "mid": mid,
                            },
                        )
                await db.execute(text("DELETE FROM check_results"))
                await db.execute(
                    text("""
                    WITH targets AS (
                      SELECT id,row_number() OVER(ORDER BY id)-1 AS slot FROM monitors
                      WHERE :fleet > 1 OR id=:mid
                    ), generated AS (
                      SELECT i, (i-1)%:fleet AS slot, (i-1)/:fleet AS seq
                      FROM generate_series(1,:n) i
                    )
                    INSERT INTO check_results
                      (id,monitor_id,checked_at,success,status_code,response_ms,error,config_version,interval_seconds)
                    SELECT gen_random_uuid(),t.id,
                      CAST(:ending AS timestamptz) - interval '30 days'
                        + g.seq * (2592000.0/(:n/:fleet))*interval '1 second',
                      g.i%10!=0, CASE WHEN g.i%10=0 THEN 500 ELSE 200 END,20,NULL,1,30
                    FROM generated g JOIN targets t USING(slot)
                """),
                    {"n": total, "ending": end, "fleet": fleet, "mid": mid},
                )
                await db.execute(text("ANALYZE check_results"))
            timings = []
            for _ in range(8):
                tick = time.perf_counter()
                async with Session() as db:
                    data = await aggregate(db, mid, "30d", end)
                timings.append(time.perf_counter() - tick)
            async with Session() as db:
                sizes = (
                    (
                        await db.execute(
                            text("""
                    SELECT count(*) AS rows,pg_table_size('check_results') AS table_bytes,
                           pg_indexes_size('check_results') AS index_bytes FROM check_results
                """)
                        )
                    )
                    .mappings()
                    .one()
                )
                plan_query = text(
                    "EXPLAIN (ANALYZE, BUFFERS, FORMAT JSON) " + BUCKET_SQL.text
                ).bindparams(
                    bindparam("start", type_=DateTime(timezone=True)),
                    bindparam("end", type_=DateTime(timezone=True)),
                    bindparam("width", type_=Integer),
                    bindparam("buckets", type_=Integer),
                )
                plan = await db.scalar(
                    plan_query,
                    {
                        "mid": mid,
                        "start": end - timedelta(days=30),
                        "end": end,
                        "width": 7200,
                        "buckets": 360,
                    },
                )
            assert data["samples"] == total // fleet and len(data["buckets"]) == 360
            report["datasets"].append(
                {
                    **dict(sizes),
                    "fleet": fleet,
                    "queried_monitor_rows": data["samples"],
                    "first_seconds": timings[0],
                    **quantiles(timings[1:]),
                    "buckets": len(data["buckets"]),
                    "json_bytes": len(json.dumps(data, default=str).encode()),
                    "plan": plan,
                }
            )
        report["status"] = "PASS"
    except Exception as exc:
        report.update(status="FAIL", error=f"{type(exc).__name__}: {exc}")
        raise
    finally:
        report["ended_at"] = now().isoformat()
        await asyncio.to_thread(
            Path("/evidence/phase6-history-benchmark.json").write_text,
            json.dumps(report, indent=2, default=str),
        )
        await engine.dispose()


if __name__ == "__main__":
    asyncio.run(main())
