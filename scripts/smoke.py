"""Real HTTP smoke test; creates and deletes only its own monitor."""
import json
import time
import urllib.error
import urllib.request
import uuid
from datetime import datetime, timezone
from pathlib import Path

BASE = "http://127.0.0.1:8080"


def call(path, payload=None, method=None):
    data = json.dumps(payload).encode() if payload is not None else None
    req = urllib.request.Request(BASE + path, data=data, method=method,
                                 headers={"Content-Type": "application/json"})
    with urllib.request.urlopen(req, timeout=10) as response:
        raw = response.read()
        return json.loads(raw) if raw else None


def main():
    start = time.monotonic()
    report = {"started_at": datetime.now(timezone.utc).isoformat(), "checks": {}}
    monitor = None
    try:
        assert call("/api/ready")["status"] == "ready"
        with urllib.request.urlopen(BASE, timeout=5) as response:
            assert "ServicePulse" in response.read().decode()
        report["checks"]["frontend_and_database_ready"] = "PASS"
        monitor = call("/api/monitors", {
            "name": f"Smoke {uuid.uuid4().hex[:8]}", "url": "http://simulator:8090/target/smoke",
            "expected_body": "ServicePulse ready", "interval_seconds": 30,
        })
        deadline = time.monotonic() + 20
        while time.monotonic() < deadline:
            saved = call(f"/api/monitors/{monitor['id']}")
            if saved["last_checked_at"]:
                break
            time.sleep(.5)
        assert saved["state"] == "UP", saved
        assert saved["last_status_code"] == 200
        history = call(f"/api/monitors/{monitor['id']}/results")
        assert history[0]["success"] and history[0]["status_code"] == 200
        report["checks"]["create_worker_http_persist_read"] = "PASS"
        report["observation"] = saved
        call(f"/api/monitors/{monitor['id']}/run", method="POST")
        report["checks"]["manual_queue"] = "PASS"
        report["result"] = "PASS"
    except Exception as exc:
        report["result"] = "FAIL"
        report["error"] = repr(exc)
        raise
    finally:
        if monitor:
            call(f"/api/monitors/{monitor['id']}", method="DELETE")
        report["elapsed_seconds"] = round(time.monotonic() - start, 3)
        Path("artifacts").mkdir(exist_ok=True)
        Path("artifacts/smoke.json").write_text(json.dumps(report, indent=2), encoding="utf-8")
        print(json.dumps(report, indent=2))


if __name__ == "__main__":
    main()
