"""Derive bounded summaries from the saved actual load experiment, without new HTTP traffic."""

import json
from collections import defaultdict
from datetime import datetime
from pathlib import Path

from phase6_load import summary

report = json.loads(Path("artifacts/phase6-load.json").read_text())
events = [
    json.loads(line)
    for line in Path("artifacts/phase6-load-events.jsonl").read_text().splitlines()
]
seen, steady, cadence, last_start = set(), [], [], {}
for item in events:
    if item["measurement"] != "http_start":
        continue
    mid = item["monitor_id"]
    at = datetime.fromisoformat(item["at"])
    if mid in seen:
        steady.append((at - datetime.fromisoformat(item["due_at"])).total_seconds())
        cadence.append((at - last_start[mid]).total_seconds())
    seen.add(mid)
    last_start[mid] = at
cpu, memory = defaultdict(list), defaultdict(list)
units = {"B": 1, "KiB": 1024, "MiB": 1024**2, "GiB": 1024**3}
for sample in report["resource_samples"]:
    for item in sample["containers"]:
        cpu[item["Name"]].append(float(item["CPUPerc"].rstrip("%")))
        raw = item["MemUsage"].split("/")[0].strip()
        for unit in sorted(units, key=len, reverse=True):
            if raw.endswith(unit):
                memory[item["Name"]].append(float(raw[: -len(unit)]) * units[unit])
                break
result = {
    "source": "phase6-load.json + phase6-load-events.jsonl",
    "steady_delay_seconds": summary(steady),
    "mixed_fixed_delay_start_cadence_seconds": summary(cadence),
    "cpu_percent_samples": {key: summary(values) for key, values in cpu.items()},
    "container_memory_usage_bytes_samples": {
        key: summary(values) for key, values in memory.items()
    },
    "limits": [
        "Docker MemUsage, not process RSS or host peak; sampled, not continuous",
        "Initial due delay includes fixture provisioning while worker stopped",
        "Other local Compose regression/browser/build activity shared the Docker host",
        "No unbounded suspension or sustained multi-worker fault guarantee",
    ],
}
Path("artifacts/phase6-load-analysis.json").write_text(json.dumps(result, indent=2))
print(json.dumps(result, indent=2))
