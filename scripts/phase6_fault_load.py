"""Fault/configuration experiment on 50 real monitors; never touches the main project."""

import json
import subprocess
import time
import urllib.error
import uuid
from datetime import UTC, datetime
from pathlib import Path

import phase4_fault_smoke as h
from phase6_load import summary

PROJECT = "servicepulse-phase6-fault-load-" + uuid.uuid4().hex[:6]
h.PREFIX = ["docker", "compose", "-p", PROJECT, "-f", "compose.performance.yaml"]
BASE = "http://127.0.0.1:19000/api"


def call(path, payload=None, method=None, expected=200):
    return h.call(path, payload, method, expected, base=BASE)


def control(name, **values):
    code = (
        "import json,sys,urllib.request; urllib.request.urlopen(urllib.request.Request("
        "'http://simulator:8090/control/'+sys.argv[1],data=sys.argv[2].encode(),"
        "headers={'Content-Type':'application/json'},method='PUT')).close()"
    )
    h.compose("exec", "-T", "backend", "python", "-c", code, name, json.dumps(values))


def results(m):
    return call(f"/monitors/{m['id']}/results")


def run(m):
    before = len(results(m))
    call(f"/monitors/{m['id']}/run", method="POST", expected=202)
    h.wait(lambda: len(results(m)) > before, seconds=60)


def snapshot():
    sql = """SELECT json_build_object('at',now(),'results',(SELECT count(*) FROM check_results),
      'monitors',(SELECT count(*) FROM monitors),'open_incidents',(SELECT count(*) FROM incidents WHERE closed_at IS NULL),
      'duplicate_open',(SELECT count(*) FROM (SELECT monitor_id FROM incidents WHERE closed_at IS NULL GROUP BY monitor_id HAVING count(*)>1)t),
      'due_without_lease',(SELECT count(*) FROM monitors WHERE state!='PAUSED' AND lease_token IS NULL AND next_due_at<=now()),
      'xact_commit',xact_commit,'xact_rollback',xact_rollback,'blks_read',blks_read,'blks_hit',blks_hit)
      FROM pg_stat_database WHERE datname=current_database()"""
    return json.loads(
        h.compose(
            "exec",
            "-T",
            "db",
            "psql",
            "-U",
            "servicepulse",
            "-d",
            "servicepulse_test",
            "-At",
            "-c",
            sql,
        ).stdout
    )


def main():
    report = {
        "started_at": datetime.now(UTC).isoformat(),
        "project": PROJECT,
        "checks": {},
    }
    started = time.monotonic()
    stop = Path("artifacts/local/fault-browser-stop")
    stop.parent.mkdir(exist_ok=True)
    stop.unlink(missing_ok=True)
    ready = Path("artifacts/local/fault-browser-ready")
    ready.unlink(missing_ok=True)
    browser = None
    try:
        config = json.loads(h.compose("config", "--format", "json").stdout)
        assert config["name"] == PROJECT
        assert (
            config["services"]["db"]["environment"]["POSTGRES_DB"]
            == "servicepulse_test"
        )
        h.compose("up", "-d", "--build", "--wait")
        monitors = []
        for index in range(50):
            name = f"fault-{index:02d}"
            delay = 32 if index == 47 else 8 if index == 49 else 0.1
            status = 500 if index == 48 else 200
            control(name, delay=delay, status=status)
            monitors.append(
                call(
                    "/monitors",
                    {
                        "name": name,
                        "url": f"http://simulator:8090/target/{name}",
                        "interval_seconds": 30,
                        "timeout_seconds": 40 if index == 47 else 2,
                    },
                    expected=201,
                )
            )
        h.wait(lambda: all(results(m) for m in monitors), seconds=60)
        assert len(call("/monitors")) == 50
        report["initial"] = snapshot()
        browser = subprocess.Popen(
            ["node", "scripts/fault-browser.mjs"], cwd="frontend"
        )
        h.wait(lambda: ready.exists(), seconds=60)
        m = monitors[0]
        control("fault-00", status=500)
        run(m)
        run(m)
        h.wait(lambda: call(f"/monitors/{m['id']}")["state"] == "DOWN")
        time.sleep(4)
        control("fault-00", status=200)
        run(m)
        time.sleep(4)
        report["checks"]["real_threshold_down_recovery"] = "PASS"

        before = results(monitors[1])
        tick = time.monotonic()
        h.compose("restart", "worker")
        h.wait(lambda: len(results(monitors[1])) > len(before), seconds=65)
        report["worker_recovery_seconds"] = time.monotonic() - tick
        assert {r["id"] for r in before}.issubset(
            {r["id"] for r in results(monitors[1])}
        )
        assert call(f"/monitors/{monitors[1]['id']}")["state"] == "UP"
        report["checks"]["worker_restart_preserves_history_and_resumes"] = "PASS"

        before = results(monitors[1])
        h.compose("stop", "db")
        try:
            call("/ready")
            raise AssertionError("DB outage unexpectedly ready")
        except (urllib.error.HTTPError, OSError):
            pass
        time.sleep(3)
        tick = time.monotonic()
        h.compose("start", "db")
        h.wait(lambda: call("/ready")["status"] == "ready")
        h.wait(lambda: len(results(monitors[1])) > len(before), seconds=65)
        report["db_recovery_seconds"] = time.monotonic() - tick
        assert {r["id"] for r in before}.issubset(
            {r["id"] for r in results(monitors[1])}
        )
        report["checks"]["postgres_outage_integrity_and_resume"] = "PASS"

        paused = monitors[2]
        call(f"/monitors/{paused['id']}/pause", {"config_version": 1}, method="POST")
        count = len(results(paused))
        target = monitors[4]
        control("fault-04", delay=3)
        prior_ids = {r["id"] for r in results(target)}
        call(f"/monitors/{target['id']}/run", method="POST", expected=202)
        h.wait(lambda: call(f"/monitors/{target['id']}")["is_running"])
        payload = {
            k: target[k]
            for k in (
                "name",
                "url",
                "interval_seconds",
                "timeout_seconds",
                "expected_status",
                "expected_body",
                "failure_threshold",
                "config_version",
            )
        }
        payload["expected_body"] = "ServicePulse ready"
        call(f"/monitors/{target['id']}", payload, method="PUT")
        h.wait(lambda: not call(f"/monitors/{target['id']}")["is_running"])
        h.wait(
            lambda: any(
                r["id"] not in prior_ids and r["config_version"] == 2
                for r in results(target)
            ),
            seconds=65,
        )
        assert all(
            r["config_version"] == 2
            for r in results(target)
            if r["id"] not in prior_ids
        )
        group = call(
            "/groups",
            {
                "name": "Load group",
                "monitor_ids": [m["id"], target["id"]],
                "recipients": [],
            },
            expected=201,
        )
        call(
            f"/groups/{group['id']}",
            {
                "name": "Edited load group",
                "monitor_ids": [m["id"]],
                "recipients": [],
                "config_version": 1,
            },
            method="PUT",
        )
        deleted = monitors[3]
        call(
            f"/monitors/{deleted['id']}?config_version=1", method="DELETE", expected=204
        )
        call(
            "/monitors",
            {
                "name": "fault-replacement",
                "url": "http://simulator:8090/target/fault-replacement",
                "interval_seconds": 30,
            },
            expected=201,
        )
        time.sleep(31)
        assert len(results(paused)) == count
        call(f"/monitors/{paused['id']}/resume", {"config_version": 2}, method="POST")
        h.wait(lambda: len(results(paused)) > count)
        report["checks"]["edit_pause_resume_delete_group_changes"] = "PASS"
        h.compose("restart", "backend")
        h.wait(lambda: call("/ready")["status"] == "ready")
        h.compose("stop", "simulator")
        run(monitors[5])
        assert results(monitors[5])[0]["success"] is False
        h.compose("start", "simulator")
        h.wait(
            lambda: (
                h.compose(
                    "exec",
                    "-T",
                    "backend",
                    "python",
                    "-c",
                    "import urllib.request; urllib.request.urlopen('http://simulator:8090/target/fault-05',timeout=2).close()",
                    check=False,
                ).returncode
                == 0
            )
        )
        run(monitors[5])
        assert results(monitors[5])[0]["success"] is True
        report["checks"]["backend_restart_simulator_outage_recovery"] = "PASS"
        latencies = []
        for _ in range(20):
            tick = time.perf_counter()
            call("/overview")
            latencies.append((time.perf_counter() - tick) * 1000)
        report["api_ms"] = summary(latencies)
        ids = h.compose("ps", "-q", "backend", "worker", "db").stdout.split()
        report["resource_snapshot"] = [
            json.loads(s)
            for s in subprocess.run(
                ["docker", "stats", "--no-stream", "--format", "{{json .}}", *ids],
                capture_output=True,
                text=True,
                check=True,
            ).stdout.splitlines()
        ]
        report["final"] = snapshot()
        assert report["final"]["duplicate_open"] == 0
        stop.write_text("finish")
        assert browser.wait(timeout=40) == 0
        report["checks"]["two_browser_clients_sse_incidents_reconnect"] = "PASS"
        raw = h.compose("logs", "--no-color", "--no-log-prefix", "worker").stdout
        Path("artifacts/phase6-fault-load-worker.log").write_text(raw, encoding="utf-8")
        report["status"] = "PASS"
    except Exception as exc:
        report.update(status="FAIL", error=f"{type(exc).__name__}: {exc}")
        raise
    finally:
        stop.write_text("finish")
        if browser is not None and browser.poll() is None:
            try:
                browser.wait(timeout=40)
            except subprocess.TimeoutExpired:
                browser.terminate()
                report["browser_shutdown"] = "Timed out; terminated"
        report["elapsed_seconds"] = time.monotonic() - started
        report["ended_at"] = datetime.now(UTC).isoformat()
        Path("artifacts/phase6-fault-load.json").write_text(
            json.dumps(report, indent=2)
        )
        h.compose("down", "--remove-orphans", check=False)
        print(json.dumps(report, indent=2))


if __name__ == "__main__":
    main()
