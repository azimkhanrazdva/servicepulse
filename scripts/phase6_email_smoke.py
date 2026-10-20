"""Actual delayed-dispatcher and SMTP-outage recovery; isolated disposable Compose project."""

import json
import time
import uuid
from datetime import UTC, datetime
from pathlib import Path

import phase4_fault_smoke as harness


def main():
    started = time.monotonic()
    project = "servicepulse-phase6-email"
    harness.PROJECT = project
    harness.PREFIX = [
        "docker",
        "compose",
        "-p",
        project,
        "-f",
        "compose.notifications-test.yaml",
    ]
    # The harness ports are exclusive; never run concurrently with phase4_fault_smoke.
    report = {
        "started_at": datetime.now(UTC).isoformat(),
        "project": project,
        "checks": {},
    }
    try:
        config = json.loads(harness.compose("config", "--format", "json").stdout)
        assert config["name"] == project
        assert (
            config["services"]["db"]["environment"]["POSTGRES_DB"]
            == "servicepulse_test"
        )
        harness.compose("up", "-d", "--build", "--wait")
        harness.compose("stop", "dispatcher")
        marker = "phase6-email-" + uuid.uuid4().hex[:8]
        m, _, email = harness.new_case(marker)
        incident = harness.fail(m, marker)
        harness.run(m)
        harness.run(m)
        assert not harness.mail(email)
        harness.control(marker, 200)
        harness.run(m)
        rows = harness.deliveries(incident)
        assert len(rows) == 2 and all(d["attempts"] == 0 for d in rows)
        ids = {d["id"] for d in rows}
        harness.compose("restart", "backend", "worker")
        harness.wait(lambda: harness.call("/ready")["status"] == "ready")
        assert harness.call(f"/monitors/{m['id']}")["state"] == "UP"
        harness.compose("start", "dispatcher")
        harness.wait(lambda: len(harness.mail(email)) == 2)
        messages = sorted(harness.mail(email), key=lambda item: item["Created"])
        assert "DOWN:" in messages[0]["Subject"]
        assert "RECOVERY:" in messages[1]["Subject"]
        assert {d["id"] for d in harness.deliveries(incident)} == ids
        assert all(d["status"] == "SENT" for d in harness.deliveries(incident))
        report["checks"][
            "offline_dispatcher_quick_recovery_restart_order_and_dedup"
        ] = "PASS"
        report["messages"] = [
            {k: item[k] for k in ("ID", "Subject", "Created")} for item in messages
        ]

        retry_marker = marker + "-retry"
        m2, _, email2 = harness.new_case(retry_marker)
        harness.compose("stop", "mailpit")
        incident2 = harness.fail(m2, retry_marker)
        harness.wait(
            lambda: any(
                d["attempts"] > 0 and d["last_error"]
                for d in harness.deliveries(incident2)
            )
        )
        harness.control(retry_marker, 200)
        harness.run(m2)
        ids2 = {d["id"] for d in harness.deliveries(incident2)}
        harness.compose("restart", "dispatcher")
        harness.compose("start", "mailpit")
        harness.wait(lambda: len(harness.mail(email2)) == 2, seconds=70)
        messages2 = sorted(harness.mail(email2), key=lambda item: item["Created"])
        assert (
            "DOWN:" in messages2[0]["Subject"]
            and "RECOVERY:" in messages2[1]["Subject"]
        )
        assert {d["id"] for d in harness.deliveries(incident2)} == ids2
        assert all(d["status"] == "SENT" for d in harness.deliveries(incident2))
        report["checks"][
            "smtp_refusal_recovery_before_retry_and_dispatcher_restart"
        ] = "PASS"
        report["retry_attempts"] = {
            d["event_type"]: d["attempts"] for d in harness.deliveries(incident2)
        }
        report["status"] = "PASS"
    except Exception as exc:
        report.update(status="FAIL", error=f"{type(exc).__name__}: {exc}")
        raise
    finally:
        cleanup = harness.compose("down", "-v", "--remove-orphans", check=False)
        if cleanup.returncode:
            report.update(status="FAIL", cleanup_error=cleanup.stderr[-1000:])
        report["ended_at"] = datetime.now(UTC).isoformat()
        report["elapsed_seconds"] = round(time.monotonic() - started, 3)
        Path("artifacts/phase6-email-smoke.json").write_text(
            json.dumps(report, indent=2), encoding="utf-8"
        )
        print(json.dumps(report, indent=2))
        if cleanup.returncode:
            raise RuntimeError("Isolated project cleanup failed")


if __name__ == "__main__":
    main()
