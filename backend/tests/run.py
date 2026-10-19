"""Reset ONLY the disposable test DB, verify migrations, then execute pytest."""

import asyncio
import os
import subprocess
import sys
import uuid
from pathlib import Path

from sqlalchemy import text
from sqlalchemy.engine import make_url

from app.db import engine
from app.models import Base


async def reset_test_schema():
    target = os.environ.get("TEST_DATABASE_URL", "")
    if (
        not target
        or target != os.environ.get("DATABASE_URL")
        or make_url(target).database != "servicepulse_test"
    ):
        raise RuntimeError("Refusing reset: matching disposable servicepulse_test URLs required")
    async with engine.begin() as connection:
        await connection.run_sync(Base.metadata.drop_all)
        await connection.execute(text("DROP TABLE IF EXISTS alembic_version"))
    await engine.dispose()


async def legacy_fixture(monitor_id, result_id, verify=False):
    async with engine.begin() as connection:
        if not verify:
            await connection.execute(
                text("""
                INSERT INTO monitors
                (id,name,url,interval_seconds,timeout_seconds,expected_status,expected_body,
                 failure_threshold,state,consecutive_failures,last_checked_at,last_status_code,
                 last_response_ms,created_at,next_due_at,lease_token,lease_until)
                VALUES (:id,'Legacy fixture','http://example.com',30,5,200,'ready',2,
                        'UP',0,now(),200,12,now(),now(),NULL,NULL)
            """),
                {"id": monitor_id},
            )
            await connection.execute(
                text("""
                INSERT INTO check_results
                (id,monitor_id,checked_at,success,status_code,response_ms,error)
                VALUES (:rid,:mid,now(),true,200,12,NULL)
            """),
                {"rid": result_id, "mid": monitor_id},
            )
        else:
            row = (
                (
                    await connection.execute(
                        text("""
                SELECT m.name,m.url,m.interval_seconds,m.expected_body,m.state,m.config_version,
                       r.id AS result_id,r.config_version AS result_version
                FROM monitors m JOIN check_results r ON r.monitor_id=m.id WHERE m.id=:id
            """),
                        {"id": monitor_id},
                    )
                )
                .mappings()
                .one()
            )
            assert row["name"] == "Legacy fixture" and row["url"] == "http://example.com"
            assert row["interval_seconds"] == 30 and row["expected_body"] == "ready"
            assert row["state"] == "UP" and row["config_version"] == row["result_version"] == 1
            assert row["result_id"] == result_id
            await connection.execute(text("DELETE FROM monitors WHERE id=:id"), {"id": monitor_id})
    await engine.dispose()


async def phase2_down_fixture(mid, gid, verify=False):
    async with engine.begin() as connection:
        if not verify:
            await connection.execute(
                text("""
                INSERT INTO monitors
                (id,name,url,interval_seconds,timeout_seconds,expected_status,expected_body,
                 failure_threshold,state,consecutive_failures,last_checked_at,last_status_code,
                 last_response_ms,created_at,next_due_at,config_version,run_requested)
                VALUES (:mid,'Legacy DOWN','http://example.com',60,8,200,'alive',2,
                        'DOWN',5,now(),500,9,now(),now(),7,false)
            """),
                {"mid": mid},
            )
            await connection.execute(
                text("INSERT INTO groups(id,name,config_version) VALUES (:gid,'Legacy group',3)"),
                {"gid": gid},
            )
            await connection.execute(
                text("INSERT INTO monitor_groups(group_id,monitor_id) VALUES (:gid,:mid)"),
                {"gid": gid, "mid": mid},
            )
            await connection.execute(
                text(
                    "INSERT INTO group_recipients(group_id,email) VALUES (:gid,'owner@example.com')"
                ),
                {"gid": gid},
            )
            await connection.execute(
                text("""INSERT INTO check_results
                (id,monitor_id,checked_at,success,status_code,response_ms,error,config_version)
                VALUES (:id,:mid,now(),false,500,9,'unexpected_status',7)"""),
                {"id": uuid.uuid4(), "mid": mid},
            )
        else:
            row = (
                (
                    await connection.execute(
                        text("""SELECT m.state,m.consecutive_failures,m.config_version,
                m.expected_body,m.interval_seconds,r.success,r.config_version AS result_version,
                g.config_version AS group_version,gr.email
                FROM monitors m JOIN check_results r ON r.monitor_id=m.id
                JOIN monitor_groups mg ON mg.monitor_id=m.id JOIN groups g ON g.id=mg.group_id
                JOIN group_recipients gr ON gr.group_id=g.id WHERE m.id=:mid"""),
                        {"mid": mid},
                    )
                )
                .mappings()
                .one()
            )
            assert row["state"] == "DOWN" and row["consecutive_failures"] == 5
            assert row["config_version"] == row["result_version"] == 7
            assert row["expected_body"] == "alive" and row["interval_seconds"] == 60
            assert (
                not row["success"]
                and row["group_version"] == 3
                and row["email"] == "owner@example.com"
            )
            assert (await connection.scalar(text("SELECT count(*) FROM incidents"))) == 0
            await connection.execute(text("DELETE FROM monitors WHERE id=:mid"), {"mid": mid})
            await connection.execute(text("DELETE FROM groups WHERE id=:gid"), {"gid": gid})
    await engine.dispose()


if __name__ == "__main__":
    asyncio.run(reset_test_schema())
    root = Path(__file__).resolve().parents[1]
    subprocess.run(["alembic", "upgrade", "0001"], cwd=root, check=True)
    monitor_id, result_id = uuid.uuid4(), uuid.uuid4()
    asyncio.run(legacy_fixture(monitor_id, result_id))
    subprocess.run(["alembic", "upgrade", "0002"], cwd=root, check=True)
    down_id, group_id = uuid.uuid4(), uuid.uuid4()
    asyncio.run(phase2_down_fixture(down_id, group_id))
    subprocess.run(["alembic", "upgrade", "head"], cwd=root, check=True)
    asyncio.run(phase2_down_fixture(down_id, group_id, verify=True))
    asyncio.run(legacy_fixture(monitor_id, result_id, verify=True))
    print("Migration preserved legacy monitor/settings/state/observation", flush=True)
    print(
        "0002 -> head preserved DOWN/settings/results/group/recipients; no fictional incidents",
        flush=True,
    )
    subprocess.run(["alembic", "check"], cwd=root, check=True)
    report = os.environ.get("TEST_REPORT_PATH", "/tmp/servicepulse-backend-tests.xml")
    subprocess.run(
        [sys.executable, "-m", "pytest", "-q", "-p", "no:cacheprovider", f"--junitxml={report}"],
        cwd=root,
        check=True,
    )
