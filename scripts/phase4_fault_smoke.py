"""Real Mailpit/fault scenarios in a dedicated project; never resets the owner's database."""

import json
import subprocess
import time
import urllib.error
import urllib.request
import uuid
from datetime import UTC, datetime, timedelta
from pathlib import Path

PROJECT = "servicepulse-phase4-fault"
PREFIX = ["docker", "compose", "-p", PROJECT, "-f", "compose.notifications-test.yaml"]
BASE = "http://127.0.0.1:18000/api"
MAIL = "http://127.0.0.1:18025"


def compose(*args, check=True):
    result = subprocess.run(
        [*PREFIX, *args], text=True, capture_output=True, check=check
    )
    if result.returncode and check:
        raise RuntimeError(result.stderr[-2000:])
    return result


def call(path, payload=None, method=None, expected=200, base=BASE):
    req = urllib.request.Request(
        base + path,
        method=method,
        data=json.dumps(payload).encode() if payload is not None else None,
        headers={"Content-Type": "application/json"},
    )
    with urllib.request.urlopen(req, timeout=5) as response:
        assert response.status == expected
        raw = response.read()
        return json.loads(raw) if raw else None


def wait(predicate, seconds=45):
    deadline = time.monotonic() + seconds
    while time.monotonic() < deadline:
        try:
            result = predicate()
            if result:
                return result
        except (OSError, ValueError):
            pass
        time.sleep(0.3)
    raise AssertionError("Timed out in isolated live notification scenario")


def mail(email):
    return [
        m
        for m in call("/api/v1/messages?limit=100", base=MAIL)["messages"]
        if any(t["Address"].casefold() == email for t in m["To"])
    ]


def control(marker, status):
    code = (
        "import sys,urllib.request; r=urllib.request.Request('http://simulator:8090/control/'+sys.argv[1],"
        "data=('{\"status\":'+sys.argv[2]+'}').encode(),headers={'Content-Type':'application/json'},method='PUT');"
        "urllib.request.urlopen(r).close()"
    )
    compose("exec", "-T", "backend", "python", "-c", code, marker, str(status))


def new_case(marker):
    m = call(
        "/monitors",
        {
            "name": marker,
            "url": f"http://simulator:8090/target/{marker}",
            "interval_seconds": 3600,
        },
        expected=201,
    )
    wait(lambda: call(f"/monitors/{m['id']}")["state"] == "UP")
    email = marker + "@example.com"
    g = call(
        "/groups",
        {"name": marker, "monitor_ids": [m["id"]], "recipients": [email]},
        expected=201,
    )
    return m, g, email


def run(m):
    root = f"/monitors/{m['id']}"
    before = len(call(root + "/results"))
    call(root + "/run", method="POST", expected=202)
    wait(lambda: len(call(root + "/results")) == before + 1)


def fail(m, marker):
    control(marker, 500)
    run(m)
    run(m)
    assert call(f"/monitors/{m['id']}")["state"] == "DOWN"
    return call(f"/monitors/{m['id']}/incidents")["items"][0]


def maintenance(m=None, g=None):
    timestamp = datetime.now(UTC)
    return call(
        "/maintenance",
        {
            "name": "isolated maintenance",
            "monitor_id": m["id"] if m else None,
            "group_id": g["id"] if g else None,
            "start_at": (timestamp - timedelta(seconds=2)).isoformat(),
            "end_at": (timestamp + timedelta(minutes=5)).isoformat(),
        },
        expected=201,
    )


def end_soon(w):
    return call(
        f"/maintenance/{w['id']}",
        {
            k: w[k]
            for k in ("name", "monitor_id", "group_id", "start_at", "config_version")
        }
        | {"end_at": (datetime.now(UTC) + timedelta(seconds=2)).isoformat()},
        method="PUT",
    )


def deliveries(incident):
    return call(f"/notifications?incident_id={incident['id']}")["items"]


def main():
    started = time.monotonic()
    report = {
        "started_at": datetime.now(UTC).isoformat(),
        "project": PROJECT,
        "checks": {},
    }
    stem = "phase4-" + uuid.uuid4().hex[:8]
    try:
        config = json.loads(compose("config", "--format", "json").stdout)
        assert (
            config["name"] == PROJECT
            and config["services"]["db"]["environment"]["POSTGRES_DB"]
            == "servicepulse_test"
        )
        compose("up", "-d", "--build")
        wait(lambda: call("/ready")["status"] == "ready")
        wait(lambda: call("/api/v1/messages", base=MAIL) is not None)
        m, _group, email = new_case(stem + "-normal")
        call(
            "/groups",
            {
                "name": "duplicate route",
                "monitor_ids": [m["id"]],
                "recipients": [email],
            },
            expected=201,
        )
        incident = fail(m, stem + "-normal")
        wait(lambda: len(mail(email)) == 1)
        run(m)
        run(m)
        time.sleep(2.2)
        assert len(mail(email)) == 1
        control(stem + "-normal", 200)
        run(m)
        wait(lambda: len(mail(email)) == 2)
        messages = mail(email)
        assert sum("DOWN:" in x["Subject"] for x in messages) == 1
        assert sum("RECOVERY:" in x["Subject"] for x in messages) == 1
        for message in messages:
            assert (
                incident["id"]
                in call("/api/v1/message/" + message["ID"], base=MAIL)["Text"]
            )
        report["checks"]["real_smtp_down_recovery_shared_address_dedup"] = "PASS"
        report["normal_messages"] = [
            {"id": x["ID"], "subject": x["Subject"]} for x in messages
        ]

        m2, g2, email2 = new_case(stem + "-maintenance")
        w = maintenance(g=g2)
        incident2 = fail(m2, stem + "-maintenance")
        run(m2)
        assert not mail(email2)
        before = call(f"/monitors/{m2['id']}/results")
        end_soon(w)
        wait(lambda: len(mail(email2)) == 1)
        assert call(f"/monitors/{m2['id']}/results") == before
        assert call(f"/monitors/{m2['id']}")["state"] == "DOWN"
        report["checks"][
            "maintenance_keeps_checks_and_down_releases_without_new_result"
        ] = "PASS"
        recovery_window = maintenance(m=m2)
        control(stem + "-maintenance", 200)
        run(m2)
        time.sleep(2.2)
        assert len(mail(email2)) == 1
        end_soon(recovery_window)
        wait(lambda: len(mail(email2)) == 2)
        assert all(d["status"] == "SENT" for d in deliveries(incident2))
        report["checks"]["previous_down_recovery_deferred_until_maintenance_ends"] = (
            "PASS"
        )

        m3, _, email3 = new_case(stem + "-quick")
        w3 = maintenance(m=m3)
        fail(m3, stem + "-quick")
        control(stem + "-quick", 200)
        run(m3)
        end_soon(w3)
        time.sleep(4)
        assert not mail(email3)
        report["checks"]["recovered_inside_window_no_stale_pair"] = "PASS"

        m4, _, email4 = new_case(stem + "-retry")
        compose("stop", "mailpit")
        incident4 = fail(m4, stem + "-retry")
        failed = wait(
            lambda: (
                rows
                if (rows := deliveries(incident4))
                and rows[0]["attempts"] >= 1
                and rows[0]["last_error"]
                else None
            )
        )
        assert failed[0]["status"] == "PENDING" and failed[0]["last_error"] in {
            "smtp_network",
            "smtp_timeout",
        }
        before_id = failed[0]["id"]
        compose("restart", "dispatcher", "worker")
        assert deliveries(incident4)[0]["id"] == before_id
        compose("start", "mailpit")
        wait(lambda: len(mail(email4)) == 1)
        assert deliveries(incident4)[0]["id"] == before_id
        control(stem + "-retry", 200)
        run(m4)
        wait(lambda: len(mail(email4)) == 2)
        report["checks"]["real_smtp_outage_retry_and_dispatcher_worker_restart"] = (
            "PASS"
        )
        report["retry_attempts"] = next(
            d["attempts"] for d in deliveries(incident4) if d["event_type"] == "DOWN"
        )

        before_counts = {
            m["id"]: len(call(f"/monitors/{m['id']}/results")) for m in (m, m2, m3, m4)
        }
        compose("stop", "db")
        time.sleep(2)
        compose("start", "db")
        wait(lambda: call("/ready")["status"] == "ready")
        for mid, count in before_counts.items():
            assert len(call(f"/monitors/{mid}/results")) == count
        report["checks"]["isolated_postgres_outage_recovery_no_fake_observations"] = (
            "PASS"
        )

        m5, _, email5 = new_case(stem + "-accept-crash")
        compose("stop", "dispatcher")
        incident5 = fail(m5, stem + "-accept-crash")
        crashed = compose(
            "run",
            "--rm",
            "--no-deps",
            "dispatcher",
            "python",
            "tests/acceptance_crash.py",
            check=False,
        )
        assert crashed.returncode == 73, crashed.stderr[-1000:]
        wait(lambda: len(mail(email5)) == 1)
        assert deliveries(incident5)[0]["status"] == "INFLIGHT"
        control(stem + "-accept-crash", 200)
        run(m5)
        time.sleep(2.2)
        compose("start", "dispatcher")
        wait(
            lambda: (
                len(deliveries(incident5)) == 2
                and all(d["status"] == "SENT" for d in deliveries(incident5))
            )
        )
        accepted = mail(email5)
        assert sum("DOWN:" in x["Subject"] for x in accepted) >= 2
        assert sum("RECOVERY:" in x["Subject"] for x in accepted) == 1
        report["checks"][
            "crash_after_acceptance_before_ack_lease_recovery_and_order"
        ] = "PASS"
        report["acceptance_crash_physical_messages"] = len(accepted)
        report["acceptance_crash_logical_deliveries"] = len(deliveries(incident5))
        report["status"] = "PASS"
    except Exception as exc:
        report.update(status="FAIL", error=f"{type(exc).__name__}: {exc}")
        raise
    finally:
        logs = compose(
            "logs", "--no-color", "--tail", "150", "dispatcher", "worker", check=False
        )
        Path("artifacts/phase4-fault.log").write_text(
            logs.stdout + logs.stderr, encoding="utf-8"
        )
        cleanup = compose("down", "-v", "--remove-orphans", check=False)
        if cleanup.returncode:
            report.update(status="FAIL", cleanup_error=cleanup.stderr[-1000:])
        report["elapsed_seconds"] = round(time.monotonic() - started, 3)
        Path("artifacts/phase4-fault.json").write_text(
            json.dumps(report, indent=2), encoding="utf-8"
        )
        print(json.dumps(report, indent=2))
        if cleanup.returncode:
            raise RuntimeError("Isolated project cleanup failed")


if __name__ == "__main__":
    main()
