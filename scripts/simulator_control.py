"""Set one named local simulator target through the existing Compose backend container."""

import argparse
import json
import re
import subprocess
from pathlib import Path


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "target", help="A dedicated demo target name, not an existing owner's target"
    )
    parser.add_argument("--status", type=int, default=200)
    parser.add_argument("--delay", type=float, default=0)
    parser.add_argument("--body", default="ServicePulse ready")
    args = parser.parse_args()
    if not re.fullmatch(r"[A-Za-z0-9_-]{1,80}", args.target):
        parser.error("Use1..80 ASCII letters, digits, hyphens or underscores")
    if not 200 <= args.status <= 599 or not 0 <= args.delay <= 180:
        parser.error("Status must be200..599 and delay0..180 seconds")
    payload = json.dumps(
        {"status": args.status, "delay": args.delay, "body": args.body}
    )
    code = (
        "import urllib.request\n"
        f"req=urllib.request.Request('http://simulator:8090/control/{args.target}', "
        f"data={payload!r}.encode(), headers={{'Content-Type':'application/json'}}, method='PUT')\n"
        "with urllib.request.urlopen(req,timeout=5) as response: print(response.status)\n"
    )
    subprocess.run(
        ["docker", "compose", "exec", "-T", "backend", "python", "-"],
        input=code,
        text=True,
        cwd=Path(__file__).resolve().parents[1],
        check=True,
    )


if __name__ == "__main__":
    main()
