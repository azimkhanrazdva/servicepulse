"""Real incident persistence, interrupted HTTP, observation gap and >interval slow target."""

import json
import subprocess
import time
import uuid
from datetime import UTC, datetime
from pathlib import Path

from phase2_smoke import call, wait_for


def control(name, **changes):
    code = (
        "import sys,urllib.request; "
        "r=urllib.request.Request('http://simulator:8090/control/'+sys.argv[1],"
        "data=sys.argv[2].encode(),headers={'Content-Type':'application/json'},method='PUT');"
        "urllib.request.urlopen(r).close()"
    )
    subprocess.run(
        [
            "docker",
            "compose",
            "exec",
            "-T",
            "backend",
            "python",
            "-c",
            code,
            name,
            json.dumps(changes),
        ],
        check=True,
        capture_output=True,
    )


def main():
    start = time.monotonic()
    report = {"started_at": datetime.now(UTC).isoformat(), "checks": {}}
    ids = []
    marker = "phase3-" + uuid.uuid4().hex[:10]
    try:
        m = call(
            "/monitors",
            {
                "name": marker,
                "url": f"http://simulator:8090/target/{marker}",
                "interval_seconds": 3600,
                "timeout_seconds": 1,
            },
            expected=201,
        )
        ids.append(m["id"])
        root = f"/monitors/{m['id']}"
        wait_for(lambda: call(root)["state"] == "UP")

        def run():
            before = len(call(root + "/results"))
            call(root + "/run", method="POST", expected=202)
            wait_for(lambda: len(call(root + "/results")) == before + 1)

        control(marker, status=500)
        run()
        assert call(root)["state"] == "UP" and not call(root + "/incidents")["items"]
        run()
        incident = call(root + "/incidents")["items"][0]
        assert incident["state"] == "OPEN"
        run()
        assert len(call(root + "/incidents")["items"]) == 1
        report["checks"]["threshold_and_continuous_outage_one_incident"] = "PASS"

        control(marker, status=500, delay=4)
        count = len(call(root + "/results"))
        call(root + "/run", method="POST", expected=202)
        wait_for(lambda: call(root)["is_running"])
        subprocess.run(["docker", "compose", "stop", "worker"], check=True)
        assert len(call(root + "/results")) == count
        gap_start = datetime.now(UTC).isoformat()
        time.sleep(2)
        assert len(call(root + "/results")) == count
        assert call(root + "/incidents")["items"][0]["id"] == incident["id"]
        report["checks"]["cancelled_http_and_stopped_worker_no_synthetic_results"] = (
            "PASS"
        )
        report["observation_gap"] = {
            "started_at": gap_start,
            "ended_at": datetime.now(UTC).isoformat(),
        }
        subprocess.run(["docker", "compose", "restart", "backend"], check=True)
        subprocess.run(["docker", "compose", "start", "worker"], check=True)
        wait_for(lambda: len(call(root + "/results")) == count + 1, timeout=30)
        rows = call(root + "/incidents")["items"]
        assert (
            len(rows) == 1
            and rows[0]["id"] == incident["id"]
            and rows[0]["state"] == "OPEN"
        )
        assert call(root)["interval_seconds"] == 3600
        report["checks"]["restart_expired_lease_same_incident_and_config"] = "PASS"
        control(marker, status=200, delay=0)
        run()
        closed = call(root + "/incidents")["items"][0]
        assert closed["closure_reason"] == "RECOVERED" and closed["recovered_at"]
        assert closed["duration_seconds"] > 0
        run()
        assert len(call(root + "/incidents")["items"]) == 1
        report["checks"]["real_recovery_exactly_one_closed_incident"] = "PASS"

        slow_name = marker + "-slow"
        control(slow_name, status=200, delay=32)
        slow_start = time.monotonic()
        slow = call(
            "/monitors",
            {
                "name": slow_name,
                "url": f"http://simulator:8090/target/{slow_name}",
                "timeout_seconds": 40,
            },
            expected=201,
        )
        ids.append(slow["id"])
        slow_root = f"/monitors/{slow['id']}"
        wait_for(lambda: call(slow_root)["is_running"])
        run()  # healthy monitor finishes while the 32-second target is in flight
        assert call(root)["state"] == "UP" and not call(slow_root + "/results")
        remaining = 30.5 - (time.monotonic() - slow_start)
        if remaining > 0:
            time.sleep(remaining)
        assert call(slow_root)["is_running"] and not call(slow_root + "/results")
        call(slow_root + "/run", method="POST", expected=409)
        wait_for(lambda: call(slow_root)["state"] == "UP", timeout=10)
        assert len(call(slow_root + "/results")) == 1
        report["checks"][
            "32s_http_exceeds_30s_interval_fast_target_unblocked_no_overlap"
        ] = "PASS"
        report["slow_elapsed_seconds"] = round(time.monotonic() - slow_start, 3)
        report["incident_id"] = incident["id"]
        report["status"] = "PASS"
    except Exception as exc:
        report.update(status="FAIL", error=f"{type(exc).__name__}: {exc}")
        raise
    finally:
        cleanup_errors = []
        restarted = subprocess.run(
            ["docker", "compose", "start", "worker"], check=False, capture_output=True
        )
        if restarted.returncode:
            cleanup_errors.append("Could not ensure worker is running")
        for mid in ids:
            try:
                call(f"/monitors/{mid}", method="DELETE", expected=204)
            except (OSError, ValueError, AssertionError) as exc:
                cleanup_errors.append(f"{mid}: {type(exc).__name__}")
        if cleanup_errors:
            report.update(status="FAIL", cleanup_errors=cleanup_errors)
        report["elapsed_seconds"] = round(time.monotonic() - start, 3)
        Path("artifacts/phase3-smoke.json").write_text(
            json.dumps(report, indent=2), encoding="utf-8"
        )
        print(json.dumps(report, indent=2))
        if cleanup_errors:
            raise RuntimeError("Live smoke cleanup failed; inspect phase3-smoke.json")


if __name__ == "__main__":
    main()
