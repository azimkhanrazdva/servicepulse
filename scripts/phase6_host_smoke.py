"""Safe local GETs verify host rejection on management API and nginx."""

import json
import urllib.error
import urllib.request
from datetime import UTC, datetime
from pathlib import Path

report = {"started_at": datetime.now(UTC).isoformat(), "checks": []}
for port in (8000, 8080):
    for host, expected in (
        ("localhost", 200),
        ("127.0.0.1", 200),
        ("servicepulse-audit.invalid", 400),
        ("localhost.attacker.example", 400),
    ):
        request = urllib.request.Request(
            f"http://127.0.0.1:{port}/api/health", headers={"Host": host}
        )
        try:
            with urllib.request.urlopen(request, timeout=5) as response:
                status = response.status
        except urllib.error.HTTPError as exc:
            status = exc.code
        report["checks"].append(
            {"port": port, "host": host, "status": status, "expected": expected}
        )
report["status"] = (
    "PASS" if all(r["status"] == r["expected"] for r in report["checks"]) else "FAIL"
)
report["ended_at"] = datetime.now(UTC).isoformat()
Path("artifacts/phase6-host-guard.json").write_text(json.dumps(report, indent=2))
print(json.dumps(report, indent=2))
assert report["status"] == "PASS"
