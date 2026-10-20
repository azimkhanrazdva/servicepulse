"""Five-minute real HTTP/fixed-delay experiment; only its own Compose volume is disposable."""

import argparse
import json
import statistics
import subprocess
import time
import urllib.request
from datetime import UTC, datetime
from pathlib import Path

PROJECT = "servicepulse-phase6-performance"
PREFIX = ["docker", "compose", "-p", PROJECT, "-f", "compose.performance.yaml"]


def compose(*args, check=True):
    return subprocess.run([*PREFIX, *args], capture_output=True, text=True, check=check)


def request(path, payload=None, base="http://127.0.0.1:19000"):
    req = urllib.request.Request(
        base + path,
        data=json.dumps(payload).encode() if payload else None,
        headers={"Content-Type": "application/json"},
    )
    with urllib.request.urlopen(req, timeout=10) as response:
        return json.loads(response.read())


def summary(values):
    if not values:
        return None
    ordered = sorted(values)
    # Explicit nearest-rank quantiles; small experiment, not a universal latency guarantee.
    import math

    return {
        "count": len(values),
        "mean": statistics.mean(values),
        "min": ordered[0],
        "p50": ordered[math.ceil(len(ordered) * 0.50) - 1],
        "p95": ordered[math.ceil(len(ordered) * 0.95) - 1],
        "p99": ordered[math.ceil(len(ordered) * 0.99) - 1],
        "max": ordered[-1],
    }


def main(seconds):
    report = {
        "started_at": datetime.now(UTC).isoformat(),
        "project": PROJECT,
        "requested_seconds": seconds,
        "monitors": 50,
        "interval_seconds": 30,
        "policy": "next_due = persistence completion + 30s; no wall-clock catch-up",
    }
    containers, snapshots, latencies = [], [], {"api_ms": [], "dashboard_http_ms": []}
    try:
        config = json.loads(compose("config", "--format", "json").stdout)
        assert config["name"] == PROJECT
        assert (
            config["services"]["db"]["environment"]["POSTGRES_DB"]
            == "servicepulse_test"
        )
        compose("up", "-d", "--build", "--wait")
        compose("stop", "worker")
        # 35 fast/medium, 5 slow, 5 expected failures, 5 timeouts. A 32s request is > interval.
        scenarios = []
        for index in range(50):
            delay, status, expected, timeout = (
                (0.1, 200, 200, 5)
                if index < 25
                else (0.8, 201, 201, 5)
                if index < 35
                else (32, 200, 200, 40)
                if index < 40
                else (0.1, 500, 200, 5)
                if index < 45
                else (6, 200, 200, 2)
            )
            name = f"load-{index:02d}"
            scenarios.append({"name": name, "status": status, "delay": delay})
            request(
                "/api/monitors",
                {
                    "name": name,
                    "url": f"http://simulator:8090/target/{name}",
                    "interval_seconds": 30,
                    "timeout_seconds": timeout,
                    "expected_status": expected,
                },
            )
        code = (
            "import json,sys,urllib.request; "
            "[(urllib.request.urlopen(urllib.request.Request('http://simulator:8090/control/'+s['name'],"
            "data=json.dumps(s).encode(),headers={'Content-Type':'application/json'},method='PUT')).close()) "
            "for s in json.loads(sys.argv[1])]"
        )
        compose("exec", "-T", "backend", "python", "-c", code, json.dumps(scenarios))
        containers = compose(
            "ps", "--all", "-q", "worker", "db", "backend"
        ).stdout.split()
        assert len(containers) == 3
        compose("start", "worker")
        start = time.monotonic()
        report["observation_started_at"] = datetime.now(UTC).isoformat()
        while time.monotonic() - start < seconds:
            for key, path, base in [
                ("api_ms", "/api/overview", "http://127.0.0.1:19000"),
                ("dashboard_http_ms", "/", "http://127.0.0.1:19080"),
            ]:
                tick = time.perf_counter()
                with urllib.request.urlopen(base + path, timeout=10) as response:
                    assert response.status == 200
                    response.read()
                latencies[key].append((time.perf_counter() - tick) * 1000)
            stats = subprocess.run(
                [
                    "docker",
                    "stats",
                    "--no-stream",
                    "--format",
                    "{{json .}}",
                    *containers,
                ],
                capture_output=True,
                text=True,
                check=True,
            )
            snapshots.append(
                {
                    "elapsed_seconds": time.monotonic() - start,
                    "containers": [
                        json.loads(line) for line in stats.stdout.splitlines()
                    ],
                }
            )
            remaining = seconds - (time.monotonic() - start)
            if remaining > 0:
                time.sleep(min(5, remaining))
        report["observed_seconds"] = time.monotonic() - start
        # Freeze claims; SIGTERM cancels outstanding HTTP without invented observations.
        compose("stop", "worker")
        raw = compose("logs", "--no-log-prefix", "--no-color", "worker").stdout
        events = []
        for line in raw.splitlines():
            try:
                item = json.loads(line)
                if "measurement" in item:
                    events.append(item)
            except ValueError:
                pass
        assert events
        Path("artifacts/phase6-load-events.jsonl").write_text(
            "\n".join(json.dumps(e) for e in events) + "\n", encoding="utf-8"
        )
        pending, overlaps, durations, delays, completions = {}, [], [], [], []
        starts, active_area, active, previous, maximum = 0, 0.0, 0, None, 0
        for item in events:
            timestamp = datetime.fromisoformat(item["at"])
            if previous is not None:
                active_area += active * (timestamp - previous).total_seconds()
            previous = timestamp
            mid = item["monitor_id"]
            if item["measurement"] == "http_start":
                starts += 1
                if mid in pending:
                    overlaps.append(mid)
                pending[mid] = timestamp
                delays.append(
                    (timestamp - datetime.fromisoformat(item["due_at"])).total_seconds()
                )
            else:
                assert mid in pending
                del pending[mid]
                if item["outcome"] != "cancelled":
                    durations.append(item["seconds"])
                    completions.append(item)
            active = item["active"]
            maximum = max(maximum, active)
        monitors = request("/api/monitors")
        results = {
            m["name"]: request(f"/api/monitors/{m['id']}/results") for m in monitors
        }
        report.update(
            http_started=starts,
            http_finished=len(completions),
            http_cancelled=starts - len(completions),
            check_results=sum(map(len, results.values())),
            successful=sum(r["success"] for rows in results.values() for r in rows),
            max_concurrency=maximum,
            mean_concurrency=active_area / report["observed_seconds"],
            overlaps=overlaps,
            http_seconds=summary(durations),
            scheduler_delay_seconds=summary(delays),
            fast_counts=[
                len(rows)
                for name, rows in sorted(results.items())
                if int(name[-2:]) < 25
            ],
            slow_counts=[
                len(rows)
                for name, rows in sorted(results.items())
                if 35 <= int(name[-2:]) < 40
            ],
            resource_samples=snapshots,
            latency={k: summary(v) for k, v in latencies.items()},
        )
        report["failed"] = report["check_results"] - report["successful"]
        report["planned_and_missed"] = (
            "Initial 50 due; subsequent schedules are created only after persistence. "
            "No theoretical fixed-rate count or missing observations inferred; per-launch due delays reported."
        )
        assert len(monitors) == 50 and not overlaps
        assert min(report["fast_counts"]) >= 3
        assert min(report["slow_counts"]) >= 2
        assert report["check_results"] <= report["http_finished"]
        report["http_finished_without_persistence_at_shutdown"] = (
            report["http_finished"] - report["check_results"]
        )
        report["status"] = "PASS"
        Path("artifacts/phase6-load-events.jsonl").write_text(
            "\n".join(json.dumps(e) for e in events) + "\n", encoding="utf-8"
        )
    except Exception as exc:
        report.update(status="FAIL", error=f"{type(exc).__name__}: {exc}")
        raise
    finally:
        cleanup = compose("down", "-v", "--remove-orphans", check=False)
        if cleanup.returncode:
            report.update(status="FAIL", cleanup_error=cleanup.stderr[-1000:])
        report["ended_at"] = datetime.now(UTC).isoformat()
        Path("artifacts/phase6-load.json").write_text(
            json.dumps(report, indent=2), encoding="utf-8"
        )
        print(
            json.dumps(
                {k: v for k, v in report.items() if k != "resource_samples"}, indent=2
            )
        )
        if cleanup.returncode:
            raise RuntimeError("Isolated load project cleanup failed")


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--seconds", type=int, default=300)
    args = parser.parse_args()
    if args.seconds < 120:
        parser.error("At least 120s required for mixed >30s fixed-delay checks")
    main(args.seconds)
