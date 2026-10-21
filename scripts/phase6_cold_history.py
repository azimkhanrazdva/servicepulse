"""Three PostgreSQL shared-buffer-cold trials. Host OS cache is explicitly not purged."""

import json
import subprocess
import uuid
from datetime import UTC, datetime
from pathlib import Path

from phase6_load import summary

project = "servicepulse-phase6-cold-" + uuid.uuid4().hex[:6]
prefix = ["docker", "compose", "-p", project, "-f", "compose.performance.yaml"]


def compose(*args):
    return subprocess.run(
        [*prefix, *args], capture_output=True, text=True, check=True
    ).stdout


report = {
    "project": project,
    "started_at": datetime.now(UTC).isoformat(),
    "cold_definition": "PostgreSQL restarted; shared_buffers cold, host OS page cache retained",
    "trials": [],
}
try:
    config = json.loads(compose("config", "--format", "json"))
    assert (
        config["name"] == project
        and config["services"]["db"]["environment"]["POSTGRES_DB"]
        == "servicepulse_test"
    )
    compose("up", "-d", "--build", "--wait", "db", "migrate")

    def run(*args):
        return compose(
            "run",
            "--rm",
            "--no-deps",
            "backend",
            "python",
            "tests/benchmark_cold.py",
            *args,
        )

    compose("build", "backend")
    mid = run("prepare").strip()
    for trial in range(3):
        compose("restart", "db")
        compose("up", "-d", "--wait", "db")
        report["trials"].append(json.loads(run("measure", mid)))
    report["cold_seconds"] = summary(
        [t["measurements"][0]["aggregate_seconds"] for t in report["trials"]]
    )
    report["warm_seconds"] = summary(
        [
            m["aggregate_seconds"]
            for t in report["trials"]
            for m in t["measurements"][1:]
        ]
    )
    report["status"] = "PASS"
except Exception as exc:
    report.update(status="FAIL", error=str(exc), stderr=getattr(exc, "stderr", None))
    raise
finally:
    cleanup = subprocess.run(
        [*prefix, "down", "--remove-orphans"],
        capture_output=True,
        text=True,
        check=False,
    )
    report["cleanup_exit_code"] = cleanup.returncode
    report["ended_at"] = datetime.now(UTC).isoformat()
    Path("artifacts/phase6-cold-history.json").write_text(json.dumps(report, indent=2))
    print(json.dumps(report, indent=2))
