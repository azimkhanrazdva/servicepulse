"""Deploy an immutable Git checkout in its own Compose project; retain its database volume."""

import argparse
import json
import os
import shutil
import subprocess
import time
import urllib.request
import uuid
from datetime import UTC, datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def request(path, data=None, method=None):
    req = urllib.request.Request(
        "http://127.0.0.1:28080/api" + path,
        data=json.dumps(data).encode() if data is not None else None,
        method=method,
        headers={"Content-Type": "application/json"},
    )
    with urllib.request.urlopen(req, timeout=5) as response:
        raw = response.read()
        return json.loads(raw) if raw else None


def wait(predicate, seconds=60):
    deadline = time.monotonic() + seconds
    while time.monotonic() < deadline:
        try:
            result = predicate()
            if result:
                return result
        except (OSError, ValueError):
            pass
        time.sleep(0.5)
    raise AssertionError("Fresh checkout readiness/observation timed out")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source", default=str(ROOT))
    parser.add_argument("--ref", default="feat/final-acceptance-release")
    args = parser.parse_args()
    project = "servicepulse-release-" + uuid.uuid4().hex[:8]
    checkout = ROOT / "artifacts" / "local" / project
    override = checkout.parent / (project + ".yaml")
    report = {
        "project": project,
        "started_at": datetime.now(UTC).isoformat(),
        "checks": {},
    }
    started = time.monotonic()
    prefix = [
        "docker",
        "compose",
        "--project-directory",
        str(checkout),
        "--env-file",
        str(checkout / ".env"),
        "-p",
        project,
        "-f",
        str(checkout / "compose.yaml"),
        "-f",
        str(override),
    ]

    def compose(*parts, check=True):
        return subprocess.run(
            [*prefix, *parts], capture_output=True, text=True, check=check
        )

    try:
        subprocess.run(
            [
                "git",
                "clone",
                "--no-hardlinks",
                "--single-branch",
                "--branch",
                args.ref,
                args.source,
                str(checkout),
            ],
            check=True,
        )
        report["source_commit"] = subprocess.check_output(
            ["git", "-C", str(checkout), "rev-parse", "HEAD"], text=True
        ).strip()
        assert not (checkout / ".env").exists()
        shutil.copyfile(checkout / ".env.example", checkout / ".env")
        override.write_text(
            """services:
  backend:
    ports: !override ['127.0.0.1:28000:8000']
  frontend:
    ports: !override ['127.0.0.1:28080:80']
  public-frontend:
    ports: !override ['127.0.0.1:28081:80']
  mailpit:
    ports: !override ['127.0.0.1:28025:8025']
""",
            encoding="utf-8",
        )
        config = json.loads(compose("config", "--format", "json").stdout)
        assert config["name"] == project
        assert config["volumes"]["pgdata"]["name"] == project + "_pgdata"
        assert (
            config["services"]["worker"]["environment"]["SIMULATOR_ORIGIN"]
            == "http://simulator:8090"
        )
        compose("up", "-d", "--build", "--wait")
        wait(lambda: request("/ready")["status"] == "ready")
        assert request("/monitors") == []
        schema = compose(
            "exec",
            "-T",
            "db",
            "psql",
            "-U",
            "servicepulse",
            "-d",
            "servicepulse",
            "-At",
            "-c",
            """
          SELECT json_build_object(
            'migration',(SELECT version_num FROM alembic_version),
            'tables',(SELECT json_agg(tablename ORDER BY tablename) FROM pg_tables WHERE schemaname='public' AND tablename!='alembic_version'),
            'constraints',(SELECT json_agg(json_build_object('table',conrelid::regclass::text,'type',contype,'definition',pg_get_constraintdef(oid))) FROM pg_constraint WHERE connamespace='public'::regnamespace),
            'indexes',(SELECT json_agg(indexdef) FROM pg_indexes WHERE schemaname='public'))
        """,
        )
        report["schema"] = json.loads(schema.stdout)
        assert report["schema"]["migration"] == "0006"
        assert len(report["schema"]["tables"]) == 12
        assert any(
            "WHERE (closed_at IS NULL)" in index
            for index in report["schema"]["indexes"]
        )
        report["checks"]["fresh_database_migrated_to_head"] = "PASS"
        monitor = request(
            "/monitors",
            {
                "name": project,
                "url": "http://simulator:8090/target/fresh-smoke",
                "interval_seconds": 30,
            },
        )
        root = "/monitors/" + monitor["id"]
        wait(lambda: request(root)["state"] == "UP")
        group = request(
            "/groups",
            {"name": project, "monitor_ids": [monitor["id"]], "recipients": []},
        )
        request(root + "/pause", {"config_version": 1}, "POST")
        previous = request(root + "/results")
        compose("restart", "db", "backend", "worker", "dispatcher")
        wait(lambda: request("/ready")["status"] == "ready")
        assert request(root)["state"] == "PAUSED"
        assert request(root + "/results") == previous
        assert request("/groups/" + group["id"])["monitor_ids"] == [monitor["id"]]
        request(root + "/resume", {"config_version": 2}, "POST")
        wait(lambda: len(request(root + "/results")) > len(previous))
        assert request(root)["state"] == "UP"
        assert {r["id"] for r in previous}.issubset(
            {r["id"] for r in request(root + "/results")}
        )
        report["checks"]["http_worker_settings_history_groups_restart"] = "PASS"
        request(root + "?config_version=3", method="DELETE")
        request("/groups/" + group["id"] + "?config_version=1", method="DELETE")
        evidence = ROOT / "artifacts/local" / (project + "-journey.json")
        env = os.environ | {
            "PLAYWRIGHT_BASE_URL": "http://127.0.0.1:28080",
            "PUBLIC_BASE_URL": "http://127.0.0.1:28081",
            "MAILPIT_BASE_URL": "http://127.0.0.1:28025",
            "SERVICEPULSE_COMPOSE_ARGS": json.dumps(prefix[2:]),
            "RELEASE_EVIDENCE_PATH": str(evidence),
        }
        runner = ROOT / "frontend/node_modules/@playwright/test/cli.js"
        result = subprocess.run(
            [
                "node",
                str(runner),
                "test",
                "e2e/release.spec.ts",
                "--workers=1",
                "--reporter=json",
                "--output=../output/playwright/phase7-clean-results",
            ],
            cwd=ROOT / "frontend",
            env=env,
            check=False,
            capture_output=True,
            text=True,
        )
        Path("artifacts/phase7-clean-browser.json").write_text(
            result.stdout, encoding="utf-8"
        )
        if result.returncode:
            raise AssertionError(
                "Fresh browser journey failed: " + result.stderr[-2000:]
            )
        report["journey"] = json.loads(evidence.read_text(encoding="utf-8"))
        assert report["journey"]["status"] == "PASS"
        report["checks"]["fresh_http_incidents_smtp_analytics_public_browser"] = "PASS"
        assert (
            subprocess.check_output(
                ["git", "-C", str(checkout), "status", "--porcelain"], text=True
            )
            == ""
        )
        report["limits"] = (
            "Fresh immutable local clone and new volume; existing Docker layer cache/host OS retained. Port override isolates owner stack; default8081 preview links tested separately."
        )
        report["status"] = "PASS"
    except Exception as exc:
        report.update(
            status="FAIL", error=str(exc), stderr=getattr(exc, "stderr", None)
        )
        raise
    finally:
        if override.exists():
            compose("logs", "--no-color", "--tail", "80", check=False)
            cleanup = compose("down", "--remove-orphans", check=False)
            report["cleanup_exit_code"] = cleanup.returncode
        report["elapsed_seconds"] = time.monotonic() - started
        report["ended_at"] = datetime.now(UTC).isoformat()
        (ROOT / "artifacts/phase7-clean-checkout.json").write_text(
            json.dumps(report, indent=2), encoding="utf-8"
        )
        print(json.dumps(report, indent=2))


if __name__ == "__main__":
    main()
