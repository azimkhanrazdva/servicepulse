"""Ensure nginx recovers when a replaced backend receives a different Docker IP."""

import json
import subprocess
import time
import uuid
from datetime import UTC, datetime
from pathlib import Path

from phase2_smoke import call, wait_for


def docker(*args):
    return subprocess.check_output(["docker", *args], text=True).strip()


def ip(container):
    networks = json.loads(docker("inspect", container))[0]["NetworkSettings"][
        "Networks"
    ]
    return networks["servicepulse_default"]["IPAddress"]


def main():
    started = time.monotonic()
    report = {"started_at": datetime.now(UTC).isoformat()}
    holder = "servicepulse-dns-test-" + uuid.uuid4().hex[:10]
    frontend = docker("compose", "ps", "-q", "frontend")
    old_backend = docker("compose", "ps", "-q", "backend")
    old_ip = ip(old_backend)
    holder_id = None
    try:
        docker("compose", "stop", "backend")
        docker("compose", "rm", "-f", "backend")
        holder_id = docker(
            "run",
            "-d",
            "--rm",
            "--name",
            holder,
            "--network",
            "servicepulse_default",
            "--ip",
            old_ip,
            "--entrypoint",
            "python",
            "servicepulse-backend",
            "-c",
            "import time; time.sleep(120)",
        )
        docker("compose", "up", "-d", "--no-deps", "backend")
        new_ip = ip(docker("compose", "ps", "-q", "backend"))
        assert new_ip != old_ip, "Fault injection did not change backend IP"
        wait_for(lambda: call("/ready")["status"] == "ready", timeout=30)
        assert docker("compose", "ps", "-q", "frontend") == frontend
        assert isinstance(call("/monitors"), list)
        assert isinstance(call("/incidents")["items"], list)
        report.update(
            status="PASS",
            old_ip=old_ip,
            new_ip=new_ip,
            frontend_container_unchanged=True,
            proxied_ready_and_api="PASS",
        )
    except Exception as exc:
        report.update(status="FAIL", error=f"{type(exc).__name__}: {exc}")
        raise
    finally:
        if holder_id:
            subprocess.run(
                ["docker", "rm", "-f", holder_id], check=True, capture_output=True
            )
        subprocess.run(
            ["docker", "compose", "up", "-d", "--no-deps", "backend"], check=True
        )
        report["elapsed_seconds"] = round(time.monotonic() - started, 3)
        Path("artifacts/proxy-recreate.json").write_text(
            json.dumps(report, indent=2), encoding="utf-8"
        )
        print(json.dumps(report, indent=2))


if __name__ == "__main__":
    main()
