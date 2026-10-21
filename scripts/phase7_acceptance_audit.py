"""Validate authored acceptance evidence; recompute retained performance and strict counts."""

import hashlib
import json
import math
import re
import subprocess
import xml.etree.ElementTree as ET
from collections import Counter
from datetime import UTC, datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def read(path):
    return json.loads((ROOT / path).read_text(encoding="utf-8-sig"))


def write(path, data):
    (ROOT / path).write_text(
        json.dumps(data, indent=2, ensure_ascii=False) + "\n", encoding="utf-8"
    )


def git(*args):
    return subprocess.check_output(
        ["git", *args], cwd=ROOT, text=True, encoding="utf-8"
    ).strip()


def quantiles(values):
    values = sorted(values)
    return {
        "count": len(values),
        **{
            key: values[min(len(values) - 1, math.ceil(p * len(values)) - 1)]
            for key, p in [("p50", 0.5), ("p95", 0.95), ("p99", 0.99), ("max", 1)]
        },
    }


def audit_events(path):
    active, starts, ends, maximum = set(), 0, 0, 0
    monitors, delays, outcomes = set(), [], Counter()
    for line in (ROOT / path).read_text(encoding="utf-8").splitlines():
        try:
            event = json.loads(line)
        except ValueError:
            continue
        kind = event.get("measurement")
        if kind == "http_start":
            mid = event["monitor_id"]
            assert mid not in active, ("overlap", mid, event)
            active.add(mid)
            monitors.add(mid)
            starts += 1
            maximum = max(maximum, len(active))
            delays.append(
                (
                    datetime.fromisoformat(event["at"])
                    - datetime.fromisoformat(event["due_at"])
                ).total_seconds()
            )
        elif kind == "http_end":
            assert event["monitor_id"] in active, event
            active.remove(event["monitor_id"])
            ends += 1
            outcomes[event["outcome"]] += 1
    assert not active and starts == ends
    return {
        "starts": starts,
        "ends": ends,
        "monitors": len(monitors),
        "maximum_concurrency": maximum,
        "overlaps": 0,
        "unfinished": 0,
        "outcomes": dict(outcomes),
        "scheduler_delay_seconds": quantiles(delays),
    }


def verify_prior_performance():
    steady = audit_events("artifacts/phase6-load-events.jsonl")
    report = read("artifacts/phase6-load.json")
    assert steady["starts"] == report["http_started"] == report["check_results"] == 475
    assert steady["monitors"] == report["monitors"] == 50
    assert steady["maximum_concurrency"] == report["max_concurrency"] == 41
    fault = audit_events("artifacts/phase6-fault-load-worker.log")
    # The mutation scenario deletes one service and creates its replacement:51 lifetime IDs,
    # while both persisted fleet snapshots contain50. Do not equate lifetime IDs with fleet size.
    faults = read("artifacts/phase6-fault-load.json")
    assert fault["starts"] == 295 and fault["monitors"] == 51
    assert faults["initial"]["monitors"] == faults["final"]["monitors"] == 50
    persisted = read("artifacts/phase6-fault-persistence-audit.json")
    assert (
        persisted["status"] == "PASS"
        and not persisted["observations_without_matching_actual_http_end"]
    )
    assert persisted["duplicate_timestamp_groups"] == 0
    history = read("artifacts/phase6-cold-history.json")
    cold, warm = [], []
    for trial in history["trials"]:
        for i, sample in enumerate(trial["measurements"]):
            assert sample["query_count"] == 2 and sample["aggregate_query_count"] == 1
            assert (
                sample["transaction_local_setting_count"] == 1
                and sample["buckets"] == 360
            )
            (cold if i == 0 else warm).append(sample["aggregate_seconds"])
    assert len(cold) == 3 and len(warm) == 21
    for label, values in [("cold_seconds", cold), ("warm_seconds", warm)]:
        actual = quantiles(values)
        assert all(abs(actual[k] - history[label][k]) < 1e-8 for k in actual)
    snapshot = read("artifacts/phase6-load-db-snapshot.json")
    browser = read("artifacts/phase6-load-browser.json")
    assert snapshot["sample_at"] < report["observation_started_at"]
    assert browser["started_at"] < report["observation_started_at"]
    result = {
        "checked_at": datetime.now(UTC).isoformat(),
        "status": "PASS",
        "steady": steady,
        "fault": fault,
        "cold_seconds": quantiles(cold),
        "warm_seconds": quantiles(warm),
        "persistence_audit": persisted,
        "attribution": "Earlier DB/browser snapshots predate final475 run. Treat as separate experiments.",
        "scope": "Recomputed retained raw events and measurements, not a new load run. Fixed delay; shared host/OS cache retained.",
    }
    write("artifacts/phase7-performance-review.json", result)
    return result


def verify_git_contract():
    anchor = "494e310bb670a141f32702b9644a3f03ee36e492"
    subprocess.run(
        ["git", "merge-base", "--is-ancestor", anchor, "HEAD"], cwd=ROOT, check=True
    )
    clean_commit = read("artifacts/phase7-clean-checkout.json")["source_commit"]
    paths = git(
        "diff",
        "--name-only",
        clean_commit,
        "--",
        "backend",
        "frontend",
        "simulator",
        "compose.yaml",
        ".env.example",
    ).splitlines()
    assert not paths, ("Runtime changed since immutable clean-checkout gate", paths)
    tracked = git("ls-files").splitlines()
    assert ".env" not in tracked and not any(
        "/node_modules/" in p or p.endswith(".pem") for p in tracked
    )
    patterns = [
        r"-----BEGIN (?:RSA |EC |OPENSSH )?PRIVATE KEY-----",
        r"gh[pousr]_" + r"[A-Za-z0-9]{30,}",
        r"AKIA" + r"[A-Z0-9]{16}",
    ]
    hits = []
    for path in tracked:
        file = ROOT / path
        if not file.is_file() or file.stat().st_size > 2_000_000:
            continue
        try:
            content = file.read_text(encoding="utf-8")
        except UnicodeError:
            continue
        if any(re.search(p, content) for p in patterns):
            hits.append(path)
    assert not hits, ("Possible secret pattern", hits)
    objects = git("rev-list", "--objects", "--all").splitlines()
    object_ids = list(dict.fromkeys(line.split()[0] for line in objects))
    metadata = (
        subprocess.check_output(
            ["git", "cat-file", "--batch-check"],
            cwd=ROOT,
            input=("\n".join(object_ids) + "\n").encode(),
        )
        .decode()
        .splitlines()
    )
    blobs = [
        line.split()[0]
        for line in metadata
        if line.split()[1] == "blob" and int(line.split()[2]) <= 2_000_000
    ]
    raw = subprocess.check_output(
        ["git", "cat-file", "--batch"],
        cwd=ROOT,
        input=("\n".join(blobs) + "\n").encode(),
    )
    offset, history_hits, scanned_text_blobs = 0, [], 0
    for oid in blobs:
        header_end = raw.index(b"\n", offset)
        size = int(raw[offset:header_end].split()[2])
        body = raw[header_end + 1 : header_end + 1 + size]
        offset = header_end + size + 2
        try:
            if b"\x00" in body:
                continue
            content = body.decode("utf-8")
        except UnicodeError:
            continue
        scanned_text_blobs += 1
        if any(re.search(p, content) for p in patterns):
            history_hits.append(oid)
    assert not history_hits, (
        "Possible history secret pattern; inspect locally",
        history_hits,
    )
    pr = read("artifacts/phase7-pr-inspection.json")
    assert len(pr["reviews"]) == 3
    result = {
        "checked_at": datetime.now(UTC).isoformat(),
        "head": git("rev-parse", "HEAD"),
        "branch": git("branch", "--show-current"),
        "phase6_anchor": anchor,
        "clean_runtime_commit": clean_commit,
        "runtime_diff_since_clean_checkout": paths,
        "limited_secret_pattern_hits": hits,
        "history_text_blobs_scanned": scanned_text_blobs,
        "history_pattern_hits": history_hits,
        "status": "PASS",
        "scope": "Current tracked UTF-8 files<=2MB; finite secret patterns, not full secret detection. No history rewrite by this stage.",
    }
    write("artifacts/phase7-git-review.json", result)
    return result


def validate_documents():
    # These tokens are review contracts, not a claim that file existence proves product behavior.
    contracts = {
        "README.md": [
            "Prerequisites",
            "docker compose up",
            "NO DATA",
            "exact model",
            "Mailpit",
            "Known limitations",
        ],
        "docs/phase7-security-review.md": [
            "SSRF",
            "Host",
            "TLS",
            "shared",
            "0 known",
            "BLOCKER",
        ],
        "docs/demo-script.md": [
            "5–10",
            "DOWN",
            "RECOVERY",
            "maintenance",
            "Public",
            "Mailpit",
        ],
        "docs/submission-guide.md": [
            "OWNER ACTION REQUIRED",
            "READY FOR OWNER APPROVAL",
            "SUBMITTED",
            "essay",
            "model",
            "private",
        ],
        "docs/release-checklist.md": [
            "150",
            "32",
            "12",
            "0006",
            "OWNER ACTION REQUIRED",
        ],
        "docs/phase7-checkpoint.md": [
            "TECHNICALLY VERIFIED",
            "READY FOR OWNER APPROVAL",
            "NOT",
            "494e310",
        ],
        "docs/phase7-performance.md": [
            "475",
            "295",
            "1.180",
            "cold",
            "warm",
            "earlier",
        ],
        "docs/ai-development.md": ["OWNER TO CONFIRM", "not a complete", "Phase7"],
        "docs/github-workflow.md": [
            "feat/final-acceptance-release",
            "gh pr create",
            "No new PR",
            "merge",
        ],
    }
    hashes = {}
    for path, tokens in contracts.items():
        content = (ROOT / path).read_text(encoding="utf-8")
        assert all(token in content for token in tokens), (path, tokens)
        for target in re.findall(r"\]\(([^)]+)\)", content):
            if not target.startswith(("http:", "https:", "#", "codex:")):
                assert ((ROOT / path).parent / target.split("#")[0]).exists(), (
                    path,
                    target,
                )
        hashes[path] = hashlib.sha256(content.encode()).hexdigest()
    result = {
        "checked_at": datetime.now(UTC).isoformat(),
        "status": "PASS",
        "reviewed_files": hashes,
        "scope": "Manual content/source review plus deterministic link/token checks. No owner essay/model/access approval inferred.",
    }
    write("artifacts/phase7-document-review.json", result)
    return result


def readiness(rows):
    counts = Counter(r["status"] for r in rows)
    denominator = sum(counts[k] for k in ["PASS", "PARTIAL", "FAIL", "NOT VERIFIED"])
    return {
        "counts": dict(counts),
        "denominator": denominator,
        "percent": round(100 * counts["PASS"] / denominator, 2)
        if denominator
        else None,
    }


def matrix():
    assert (
        readiness([{"status": s} for s in ["PASS", "PARTIAL", "NOT APPLICABLE"]])[
            "percent"
        ]
        == 50
    )
    rows = read("docs/phase7-criteria.json")["rows"]
    assert len(rows) == len({r["id"] for r in rows}) == 232
    previous_ids = set(
        re.findall(
            r"^\| ([A-Z0-9]+(?:-REQ)?-\d{2}) \|",
            git("show", "494e310:docs/requirements.md"),
            re.MULTILINE,
        )
    )
    assert len(previous_ids) == 202
    assert {r["id"] for r in rows} == previous_ids | {
        f"P7-{i:02}" for i in range(1, 31)
    }
    backend = ET.parse(ROOT / "artifacts/phase7-backend-tests.xml")
    backend_names = {c.attrib["name"] for c in backend.iter("testcase")}
    assert (
        len(backend_names) == 150
        and not list(backend.iter("failure"))
        and not list(backend.iter("skipped"))
        and not list(backend.iter("error"))
    )
    frontend = read("artifacts/phase7-frontend-tests.json")
    assert frontend["numPassedTests"] == 32 and frontend["numFailedTests"] == 0
    assert frontend["numPendingTests"] == frontend["numTodoTests"] == 0
    front_names = {
        c["title"]
        for f in frontend["testResults"]
        for c in f["assertionResults"]
        if c["status"] == "passed"
    }
    browser = read("artifacts/phase7-browser-tests.json")
    assert browser["stats"]["expected"] == 12 and not any(
        browser["stats"][k] for k in ["unexpected", "flaky", "skipped"]
    )
    for proof in [
        "artifacts/phase7-clean-checkout.json",
        "artifacts/phase7-release-journey.json",
        "artifacts/phase7-smtp-faults.json",
        "artifacts/phase7-email-continuation.json",
        "artifacts/phase7-host-guard.json",
    ]:
        assert read(proof)["status"] == "PASS", proof
    assert len(read("artifacts/phase7-smtp-faults.json")["checks"]) == 7
    assert len(read("artifacts/phase7-email-continuation.json")["checks"]) == 2
    assert (
        read("artifacts/phase7-npm-audit.json")["metadata"]["vulnerabilities"]["total"]
        == 0
    )
    assert all(
        not d["vulns"] for d in read("artifacts/phase7-pip-audit.json")["dependencies"]
    )
    scans = []
    for width in [390, 768, 1440, 1920]:
        scans.extend(read(f"artifacts/phase7-accessibility-{width}.json"))
    assert len(scans) == 12 and all(not scan["violations"] for scan in scans)
    if any(
        r["status"] == "PASS" and r["id"] in {"DEL-06", "DEL-07", "P7-24"} for r in rows
    ):
        ci = read("artifacts/phase7-ci.json")
        assert ci["status"] == "completed" and ci["conclusion"] == "success"
        assert len(ci["jobs"]) == 3 and all(
            j["conclusion"] == "success" for j in ci["jobs"]
        )
        hosted = ci["downloaded_browser_evidence"]
        assert hosted["stats"]["expected"] == 12
        assert not any(
            hosted["stats"][key] for key in ["unexpected", "flaky", "skipped"]
        )
        assert hosted["axe_scans"] == 12 and hosted["axe_violations"] == 0
        subprocess.run(
            ["git", "merge-base", "--is-ancestor", ci["headSha"], "HEAD"],
            cwd=ROOT,
            check=True,
        )
    for r in rows:
        assert r["origin"] in {"M", "O", "T", "OPT"} and r["status"] in {
            "PASS",
            "PARTIAL",
            "FAIL",
            "NOT VERIFIED",
            "NOT APPLICABLE",
        }
        for path in r["implementation"]:
            assert (ROOT / path).exists(), (r["id"], "implementation", path)
        for path in r["evidence"]:
            if r["status"] != "NOT VERIFIED":
                assert (ROOT / path).exists(), (r["id"], "evidence", path)
        for test in r["test"]:
            if test.startswith(("manual:", "command:", "owner:")):
                continue
            path, _, name = test.partition("::")
            assert (ROOT / path).exists(), (r["id"], "test path", path)
            if name:
                if path.startswith("backend/tests/test_"):
                    assert any(
                        n == name or n.startswith(name + "[") for n in backend_names
                    ), (r["id"], "unexecuted pytest", name)
                elif path.startswith("frontend/src/"):
                    assert name in front_names, (r["id"], "unexecuted component", name)
                else:
                    assert name in (ROOT / path).read_text(encoding="utf-8"), (
                        r["id"],
                        "test symbol",
                        name,
                    )
        assert r["limitation"] and r["test_result"], r["id"]
    summary = {
        origin: readiness([r for r in rows if r["origin"] == origin])
        for origin in ["M", "O", "T", "OPT"]
    }
    write(
        "artifacts/phase7-readiness.json",
        {
            "formula": "PASS/(PASS+PARTIAL+FAIL+NOT VERIFIED)*100; NOT APPLICABLE excluded only with justification",
            "origins": summary,
            "mandatory_project": readiness([r for r in rows if r["origin"] != "OPT"]),
            "all_rows_inventory": dict(Counter(r["status"] for r in rows)),
            "total_rows": len(rows),
        },
    )
    lines = [
        "# Phase7 — per-ID final acceptance",
        "",
        "Canonical authored ledger: [phase7-criteria.json](phase7-criteria.json). These232 split project criteria are not232 employer requirements. M=employer, O=owner, T=engineering, OPT=optional choice. Baseline133 +69 earlier phase additions +30 final acceptance criteria. No weighted credit for PARTIAL. NOT APPLICABLE excluded only with an explicit reason.",
        "",
        "| Origin | PASS | PARTIAL | FAIL | NOT VERIFIED | NOT APPLICABLE | Strict % |",
        "|---|---:|---:|---:|---:|---:|---:|",
    ]
    for origin, value in summary.items():
        c = value["counts"]
        lines.append(
            f"| {origin} | "
            + " | ".join(
                str(c.get(k, 0))
                for k in ["PASS", "PARTIAL", "FAIL", "NOT VERIFIED", "NOT APPLICABLE"]
            )
            + f" | {value['percent']} |"
        )
    lines += [
        "",
        "Product acceptance and submission are separate. GEN-07 exact model and DEL-18 employer access remain incomplete; personal essay is an owner obligation. Optional authentication is a deployment choice, not an implemented login. Scope limitations remain attached to every row.",
        "",
        "| ID / origin / priority | Requirement / acceptance scope | Implementation | Concrete verification | Actual result / evidence | Status / limits |",
        "|---|---|---|---|---|---|",
    ]

    def link(p):
        return f"[{p}]({'../' if not p.startswith('docs/') else ''}{p if not p.startswith('docs/') else p[5:]})"

    def safe(s):
        return s.replace("|", "\\|").replace("\n", " ")

    for r in rows:
        columns = [
            r["id"] + " / " + r["origin"] + " / " + r["priority"],
            r["requirement"]
            + "; "
            + r.get(
                "acceptance",
                "Satisfy the stated behavior within the verification scope below.",
            ),
            "; ".join(link(p) for p in r["implementation"]),
            "; ".join(r["test"]),
            r["test_result"] + "; " + "; ".join(link(p) for p in r["evidence"]),
            r["status"] + ": " + r["limitation"],
        ]
        lines.append("| " + " | ".join(safe(c) for c in columns) + " |")
    (ROOT / "docs/phase7-final-acceptance.md").write_text(
        "\n".join(lines) + "\n", encoding="utf-8"
    )
    print(json.dumps(summary, indent=2))


if __name__ == "__main__":
    verify_prior_performance()
    verify_git_contract()
    validate_documents()
    matrix()
