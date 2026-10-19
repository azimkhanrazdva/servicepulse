"""Live config/pause/persistence/restart checks; touches only uniquely named test resources."""

import json
import subprocess
import time
import urllib.error
import urllib.request
import uuid
from datetime import UTC, datetime
from pathlib import Path

BASE = "http://127.0.0.1:8080/api"


def call(path, payload=None, method=None, expected=200):
    req = urllib.request.Request(
        BASE + path,
        method=method,
        data=json.dumps(payload).encode() if payload is not None else None,
        headers={"Content-Type": "application/json"},
    )
    try:
        with urllib.request.urlopen(req, timeout=10) as response:
            assert response.status == expected, (response.status, path)
            raw = response.read()
            return json.loads(raw) if raw else None
    except urllib.error.HTTPError as exc:
        if exc.code == expected:
            return None
        raise


def wait_for(predicate, timeout=40):
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        try:
            value = predicate()
            if value:
                return value
        except (urllib.error.URLError, TimeoutError):
            pass
        time.sleep(0.3)
    raise AssertionError("Timed out waiting for live worker/API")


def settings(monitor, **changes):
    keys = [
        "name",
        "url",
        "interval_seconds",
        "timeout_seconds",
        "expected_status",
        "expected_body",
        "failure_threshold",
        "config_version",
    ]
    return {**{key: monitor[key] for key in keys}, **changes}


def main():
    started = time.monotonic()
    report = {"started_at": datetime.now(UTC).isoformat(), "checks": {}}
    monitor = group = None
    marker = "phase2-" + uuid.uuid4().hex[:10]
    try:
        monitor = call(
            "/monitors",
            {"name": marker, "url": f"http://simulator:8090/target/{marker}"},
            expected=201,
        )
        root = f"/monitors/{monitor['id']}"
        monitor = wait_for(lambda: m if (m := call(root))["state"] == "UP" else None)
        monitor = call(root + "/pause", {"config_version": monitor["config_version"]})
        before = call(root + "/results")
        call(root + "/run", method="POST", expected=409)
        time.sleep(
            31
        )  # exceeds the original 30-second interval; do not fake the pause test
        assert call(root + "/results") == before
        report["checks"]["pause_over_original_interval"] = "PASS"
        monitor = call(
            root,
            settings(
                monitor,
                name=marker + " edited",
                interval_seconds=60,
                timeout_seconds=8,
                expected_body="ServicePulse ready",
            ),
            method="PUT",
        )
        group = call(
            "/groups",
            {
                "name": marker,
                "monitor_ids": [monitor["id"]],
                "recipients": ["ops@example.com"],
            },
            expected=201,
        )
        assert group["state"] == "PAUSED"
        monitor = call(root + "/resume", {"config_version": monitor["config_version"]})
        wait_for(lambda: call(root)["state"] == "UP")
        before_manual = len(call(root + "/results"))
        call(root + "/run", method="POST", expected=202)
        wait_for(lambda: len(call(root + "/results")) > before_manual)
        report["checks"]["manual_run_persists_new_observation"] = "PASS"

        control_code = (
            "import json,sys,urllib.request; "
            "r=urllib.request.Request('http://simulator:8090/control/'+sys.argv[1], "
            "data=json.dumps({'delay':4}).encode(),headers={'Content-Type':'application/json'}, "
            "method='PUT'); urllib.request.urlopen(r).close()"
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
                control_code,
                marker,
            ],
            check=True,
        )
        call(root + "/run", method="POST", expected=202)
        wait_for(lambda: call(root)["is_running"])
        current = call(root)
        updated = call(
            root,
            settings(
                current,
                url=f"http://simulator:8090/target/{marker}-new",
                interval_seconds=90,
            ),
            method="PUT",
        )
        assert updated["is_running"] and updated["state"] == "UNKNOWN"
        call(root + "/run", method="POST", expected=409)
        saved_count = len(call(root + "/results"))
        subprocess.run(
            ["docker", "compose", "restart", "backend", "worker"], check=True
        )
        recovered = wait_for(
            lambda: m if (m := call(root))["state"] == "UP" else None, timeout=45
        )
        assert (
            recovered["url"] == updated["url"] and recovered["interval_seconds"] == 90
        )
        assert recovered["config_version"] == updated["config_version"]
        results = call(root + "/results")
        assert len(results) == saved_count + 1
        assert results[0]["config_version"] == updated["config_version"]
        assert all(row["success"] for row in results)
        saved_group = call(f"/groups/{group['id']}")
        assert saved_group["monitor_ids"] == [monitor["id"]]
        assert (
            saved_group["recipients"] == ["ops@example.com"]
            and saved_group["state"] == "UP"
        )
        report["checks"]["edit_during_real_http_keeps_lease"] = "PASS"
        report["checks"]["backend_worker_restart_preserves_config_and_group"] = "PASS"
        report["checks"]["restart_has_no_synthetic_failures_or_stale_result"] = "PASS"
        report["observations"] = {
            "before_restart": saved_count,
            "after_restart": len(results),
            "latest_config_version": results[0]["config_version"],
        }
        report["result"] = "PASS"
    except Exception as exc:
        report["result"] = "FAIL"
        report["error"] = repr(exc)
        raise
    finally:
        if group:
            call(
                f"/groups/{group['id']}?config_version={group['config_version']}",
                method="DELETE",
                expected=204,
            )
        if monitor:
            call(f"/monitors/{monitor['id']}", method="DELETE", expected=204)
        report["elapsed_seconds"] = round(time.monotonic() - started, 3)
        Path("artifacts/phase2-smoke.json").write_text(
            json.dumps(report, indent=2), encoding="utf-8"
        )
        print(json.dumps(report, indent=2))


if __name__ == "__main__":
    main()
