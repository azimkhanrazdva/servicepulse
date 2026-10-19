"""Reset ONLY the disposable test DB, verify migrations, then execute pytest."""

import asyncio
import os
import subprocess
import sys
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


if __name__ == "__main__":
    asyncio.run(reset_test_schema())
    root = Path(__file__).resolve().parents[1]
    subprocess.run(["alembic", "upgrade", "head"], cwd=root, check=True)
    subprocess.run(["alembic", "check"], cwd=root, check=True)
    report = os.environ.get("TEST_REPORT_PATH", "/tmp/servicepulse-backend-tests.xml")
    subprocess.run(
        [sys.executable, "-m", "pytest", "-q", "-p", "no:cacheprovider", f"--junitxml={report}"],
        cwd=root,
        check=True,
    )
