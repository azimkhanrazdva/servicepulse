"""Reset ONLY the disposable test DB, verify migrations, then execute pytest."""

import asyncio
import os
import subprocess
import sys
import uuid
from datetime import timedelta
from pathlib import Path

from sqlalchemy import text
from sqlalchemy.engine import make_url

from app.db import Session, engine
from app.models import (
    Base,
    CheckResult,
    Incident,
    MaintenanceWindow,
    Monitor,
    NotificationEvent,
    NotificationRoute,
    Publication,
    PublicPage,
    now,
)


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


async def legacy_incidents(mid, identities, expected=None):
    async with engine.begin() as connection:
        if expected is None:
            for index, identity in enumerate(identities):
                await connection.execute(
                    text("""INSERT INTO incidents
                    (id,monitor_id,opened_at,closed_at,recovered_at,closure_reason,created_at)
                    VALUES (:id,:mid,now()-interval '2 minutes',
                    CASE WHEN :closed THEN now() ELSE NULL END,
                    CASE WHEN :closed THEN now() ELSE NULL END,
                    CASE WHEN :closed THEN 'RECOVERED' ELSE NULL END,now())"""),
                    {"id": identity, "mid": mid, "closed": bool(index)},
                )
        rows = (
            await connection.execute(
                text("""SELECT id,monitor_id,opened_at,closed_at,
                    recovered_at,closure_reason,created_at FROM incidents WHERE monitor_id=:mid
                    ORDER BY id"""),
                {"mid": mid},
            )
        ).all()
        values = [tuple(row) for row in rows]
        if expected is not None:
            assert values == expected
            assert (
                await connection.scalar(
                    text("SELECT count(*) FROM incidents WHERE notifications_enabled")
                )
            ) == 0
            assert (await connection.scalar(text("SELECT count(*) FROM notification_events"))) == 0
            await connection.execute(
                text("DELETE FROM incidents WHERE monitor_id=:mid"), {"mid": mid}
            )
    await engine.dispose()
    return values


async def phase4_fixture(expected=None):
    """Preserve actual 0004 outbox/window rows, not only the earlier schema fixtures."""
    async with Session() as db, db.begin():
        if expected is None:
            monitor = Monitor(name="0004 fixture", url="http://example.com", state="DOWN")
            db.add(monitor)
            await db.flush()
            incident = Incident(
                monitor_id=monitor.id,
                opened_at=now() - timedelta(minutes=1),
                notifications_enabled=True,
            )
            db.add(incident)
            await db.flush()
            event = NotificationEvent(
                incident_id=incident.id, event_type="DOWN", monitor_name=monitor.name
            )
            db.add(event)
            await db.flush()
            db.add(
                NotificationRoute(
                    event_id=event.id, group_id=uuid.uuid4(), email="fixture@example.com"
                )
            )
            # Raw legacy columns: the current ORM also knows additive 0006 fields.
            await db.execute(
                text("""
                INSERT INTO notification_deliveries
                (id,event_id,email,status,attempts,created_at,next_attempt_at,sent_at,send_started_at)
                VALUES (:id,:event,'fixture@example.com','SENT',2,:at,:at,:at,:at)
            """),
                {"id": uuid.uuid4(), "event": event.id, "at": now()},
            )
            db.add(
                MaintenanceWindow(
                    name="0004 window",
                    monitor_id=monitor.id,
                    start_at=now(),
                    end_at=now() + timedelta(hours=1),
                )
            )
            await db.flush()
            mid = monitor.id
        else:
            mid = expected[0]
        values = {}
        for table in (
            "maintenance_windows",
            "notification_events",
            "notification_routes",
            "notification_deliveries",
        ):
            values[table] = (
                await db.scalars(
                    text(
                        f"SELECT to_jsonb(t) - 'down_eligible_at' - 'down_required' "
                        f"FROM {table} t ORDER BY to_jsonb(t)::text"
                    )
                )
            ).all()
        if expected is not None:
            assert values == expected[1]
            assert (
                await db.scalar(
                    text(
                        "SELECT count(*) FROM notification_deliveries "
                        "WHERE down_eligible_at IS NOT NULL OR down_required"
                    )
                )
                == 0
            )
            assert await db.scalar(text("SELECT count(*) FROM public_pages")) == 0
            assert await db.scalar(text("SELECT count(*) FROM publications")) == 0
            assert (
                await db.scalar(
                    text("SELECT count(*) FROM check_results WHERE interval_seconds IS NOT NULL")
                )
                == 0
            )
            await db.execute(text("DELETE FROM monitors WHERE id=:id"), {"id": mid})
    await engine.dispose()
    return mid, values


async def phase5_fixture(expected=None):
    """An explicitly published 0005 page and captured cadence must survive 0006 unchanged."""
    async with Session() as db, db.begin():
        if expected is None:
            monitor = Monitor(name="0005 fixture", url="http://example.com", state="PAUSED")
            page = PublicPage(
                slug="migration-fixture", title="Explicit owner publication", enabled=True
            )
            db.add_all([monitor, page])
            await db.flush()
            db.add_all(
                [
                    Publication(
                        page_id=page.id,
                        monitor_id=monitor.id,
                        public_name="Published fixture",
                        show_history=True,
                    ),
                    CheckResult(
                        monitor_id=monitor.id,
                        checked_at=now(),
                        success=True,
                        response_ms=12,
                        config_version=1,
                        interval_seconds=30,
                    ),
                ]
            )
            await db.flush()
            ids = monitor.id, page.id
        else:
            ids = expected[0]
        values = {}
        for table, clause, identity in (
            ("monitors", "id", ids[0]),
            ("check_results", "monitor_id", ids[0]),
            ("public_pages", "id", ids[1]),
            ("publications", "page_id", ids[1]),
        ):
            values[table] = (
                await db.scalars(
                    text(
                        f"SELECT to_jsonb(t) FROM {table} t WHERE {clause}=:id "
                        "ORDER BY to_jsonb(t)::text"
                    ),
                    {"id": identity},
                )
            ).all()
        if expected is not None:
            assert values == expected[1]
            await db.execute(text("DELETE FROM public_pages WHERE id=:id"), {"id": ids[1]})
            await db.execute(text("DELETE FROM monitors WHERE id=:id"), {"id": ids[0]})
    await engine.dispose()
    return ids, values


if __name__ == "__main__":
    asyncio.run(reset_test_schema())
    root = Path(__file__).resolve().parents[1]
    subprocess.run(["alembic", "upgrade", "0001"], cwd=root, check=True)
    monitor_id, result_id = uuid.uuid4(), uuid.uuid4()
    asyncio.run(legacy_fixture(monitor_id, result_id))
    subprocess.run(["alembic", "upgrade", "0002"], cwd=root, check=True)
    down_id, group_id = uuid.uuid4(), uuid.uuid4()
    asyncio.run(phase2_down_fixture(down_id, group_id))
    subprocess.run(["alembic", "upgrade", "0003"], cwd=root, check=True)
    incident_ids = [uuid.uuid4(), uuid.uuid4()]
    incident_fixture = asyncio.run(legacy_incidents(down_id, incident_ids))
    subprocess.run(["alembic", "upgrade", "0004"], cwd=root, check=True)
    outbox_fixture = asyncio.run(phase4_fixture())
    subprocess.run(["alembic", "upgrade", "0005"], cwd=root, check=True)
    publication_fixture = asyncio.run(phase5_fixture())
    subprocess.run(["alembic", "upgrade", "head"], cwd=root, check=True)
    asyncio.run(phase5_fixture(publication_fixture))
    print("0005 -> head preserved explicit publication/cadence; fixture-only cleanup", flush=True)
    asyncio.run(phase4_fixture(outbox_fixture))
    print("0004 -> head preserved outbox/windows; no publication or cadence backfill", flush=True)
    asyncio.run(legacy_incidents(down_id, incident_ids, incident_fixture))
    print(
        "0003 -> head preserved incidents, notifications disabled; no email backfill",
        flush=True,
    )
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
