# Phase6 audit — in progress, not a v0.6 release approval

Started from clean `4696798247feec3dab6642555cfc8794e417bfc9`, on 2026-10-20 at
08:58:02+05:00. New branch `feat/reliability-audit-redesign` descends from that actual
Phase5 HEAD. Original commits/dates and stacked PR #1/#2/#3 remain unchanged.
Prompt preserved verbatim in prompts/006-audit-reliability-redesign.md; no session export claimed.

## Executive summary

The first Phase6 increment addresses confirmed notification, lease and public-health defects,
and adds actual isolated load/history experiments. The complete Phase6 assignment remains
PARTIAL: monochrome redesign, complete accessibility/security acceptance and fault testing
under 50-monitor load are not finished. No full-product readiness percentage is assigned.

The original PDF was actually re-extracted with `python -X utf8` and pypdf. Task3 requires
DOWN then recovery mail, suppression during maintenance, 50x30 independence, fast monthly
history and preserved gaps. The existing 133 IDs split employer, owner and engineering
criteria; requirements-provenance.md retains those distinctions. Neither monochrome design
nor an exact one-second p95 budget is a literal employer PDF requirement.

## Findings

| ID | Severity / component | Reproduction and root cause | Fix / status / evidence |
| --- | --- | --- | --- |
| P6-001 / ACC-EMAIL-01 | HIGH / outbox | Confirm DOWN then recover before dispatcher; old preflight cancels both because send_started_at is NULL | New persisted obligation/deadline in 0006; maintenance/group mutation hooks; ordered recovery. Initial failing test recorded in phase6-reproduction.xml. PostgreSQL policy and actual isolated SMTP regressions pass; see phase6-notification-policy.md. Upgrade never guesses legacy eligibility. |
| P6-002 | HIGH / worker | Expire a claim before execute, keeping its token; old preflight still invokes HTTP | Expiry guard after row lock and renewed full timeout+15s budget for valid claims. test_expired_claim_never_starts_http failed before fix and passes after. Not a guarantee against arbitrary process suspension after preflight. |
| P6-003 | MEDIUM / public | Fresh UP plus stale/no-data PAUSED returns UNKNOWN; freshness considers services omitted from active states | Filter both state and freshness to active services. Ten-case PostgreSQL table covers empty/all-paused/UP/DOWN/UNKNOWN/stale/no-data; initial two failures retained. Stale alone never creates DOWN; last observed DOWN remains visible. |
| P6-004 | MEDIUM / management boundary | Independent reviewer actual harmless GET with Host servicepulse-audit.invalid returned200 on8000 and8080 | Explicit local management Host allowlist and nginx default-host400; regression added. Full browser DNS-rebinding exploit was not performed. Public routes remain separate. |
| P6-005 | MEDIUM / analytics presentation | AnalyticsPanel gives 100% sample uptime substantially more prominence than low coverage | OPEN: pair visual prominence and clear low-coverage wording in monochrome redesign. SQL calculation not found defective. |
| P6-006 | MEDIUM / dashboard scope | UI labels loaded <=500 monitor rows as workspace total | OPEN: disclose loaded scope or implement global counts/pagination before claiming global sort/filter. |
| P6-007 | MEDIUM / navigation | App permanently assigns active class to Overview regardless of anchor | OPEN: selected section/aria-current in redesign. |
| P6-008 | MEDIUM / request UX | Fetch paths have no bounded deadline; a hung request can retain loading/busy state | OPEN: bounded timeout/error/retry without losing drafts, plus regression. |
| P6-009 | MEDIUM / mobile | Real Chromium 390px with50 rows reports document overflow; old isMobile test expands layout viewport and misses it | Mobile nav now wraps with visible labels; strict390px regression replaces emulation-only viewport check. Four real widths on50 rows passed after correction; actual baseline screenshots retained. |
| P6-010 | MEDIUM / history latency | Dense100k single-monitor first call1.143s and external-merge temporary sorts in actual plan | OPEN: warm p95~609ms meets local target, first/all-eight p95 does not. Keep bounded SQL; repeat isolated first-call trials and evaluate evidenced sort/materialization bottleneck. Exact plans/sizes/distribution in phase6-performance.md. |

Counts: ten confirmed findings, zero BLOCKER, two HIGH, eight MEDIUM, zero LOW.
New owner-requested design/features/test coverage are unfinished work, not invented old defects.
P6-001 review also identified revoked-route restoration and observation/persistence ordering
edges. Added terminal revocation and completion-timestamp reevaluation, with PostgreSQL regressions.

## Independent review provenance

Three separate Codex review agents inspected actual files: backend_review (backend/PostgreSQL/
reliability), frontend_review (UI/UX/accessibility/acceptance), security_review (SSRF/public/deployment).
They were read-only. Backend reviewer reproduced two expressions/functions with extracted code and
fake dependencies, not PostgreSQL. Security reviewer made harmless local HTTP GETs. Neither claimed
running integration suites. Root agent implemented fixes and ran the recorded real checks.
These are independent agent reviews, not independent human approval or final certification.

Lock review: group parents -> monitors in UUID order -> maintenance row; dispatcher preflight
monitor -> delivery. SMTP runs outside transactions. Claim/ack delivery locks do not acquire
monitor locks. New eligibility is persisted atomically with incident/event/observation.

## Original behavior traceability (current increment)

| Employer behavior | Existing IDs | Executable evidence / remaining boundary |
| --- | --- | --- |
| CRUD and interval/timeout/code/body | MON-01..10 | test_database.py, test_core.py; slice/management browser and smoke |
| Pause/resume | MON-06/07 | phase2_smoke.py and versioned management browser |
| Group status/recipients | GRP-01..04 | test_database.py/test_notifications.py; management browser |
| Real dashboard/status/history | UI-01..05, HIS-01 | real browser tests, persisted results and analytics SQL |
| 24h/week/month uptime and gaps | HIS-02..04, SCN-18 | test_public_analytics.py + new manual/equal-timestamp coverage test; no SQL rewrite without defect |
| Incident threshold/transient/recovery | SCN-06..08 | default-threshold notification regression, DB incident tests, phase3_smoke.py |
| DOWN/recovery/no repeated logical mail | NTF-02..08, SCN-03..05 | new quick-recovery PostgreSQL + actual phase6_email_smoke.py; existing acceptance-crash harness |
| Monitor/group maintenance, checks continue/end release | MNT-01..08, SCN-09..11 | existing maintenance browser and seven live fault groups plus new offline/deadline/edit cases |
| Private/public auto updates and two clients | SCN-01/02, GEN-11 | seven actual Chromium E2E retained, real worker HTTP and public SSE/reconnect |
| Explicit publication and privacy | PUB-01..04, SCN-16 | allowlisted REST/SSE/API isolation tests and browser revocation/privacy |
| Restart configuration/history; gaps not DOWN | SCN-17/18 | phase2/3/fault smoke, migration0001..0005 fixtures through0006 |
| No self-overlap; slow targets independent | SCN-12/14 | new expired-preflight test; actual32s/30s smoke and isolated mixed50 experiment; suspension limit disclosed |
| 50 monitors ×30s, responsive interface | SCN-13 | phase6_load.py, load events/resources, four-viewport real render; see phase6-performance.md for exact measurements/limits |
| Fast month history | HIS-09, SCN-15 | synthetic isolated PostgreSQL benchmark; dataset distribution and query plans retained, not real HTTP observations |

## Security scope and remaining work

No confirmed SSRF bypass/public private-data leak found in inspected code and current regressions.
All DNS answers validated, numeric IP pinning/Host+SNI, redirects/proxies disabled, deadline/body cap,
strict public projection, publication authorization every read/tick, no-store and loopback bindings remain.
Shared privileged DB role, no ingress rate/SSE limits/egress firewall, unverified real external TLS/
mailbox delivery and unauthenticated trusted-local management remain explicit production boundaries.
Pinned Python pip-audit and npm audit completed with zero known vulnerabilities; limited tracked
history private-key/GitHub/AWS patterns found zero matches and .env is untracked. These are
bounded checks, not a complete secret/security guarantee. The final complete security pass is
still required before Phase6 completion. No real secret was requested or sent to an external scanner.


## 2026-10-20T15:53:12+05:00 — Continuation closure review

The earlier sections describe the first checkpoint and remain as historical evidence. Current disposition:

| Finding | Current disposition | New evidence |
|---|---|---|
| P6-001..004 | Prior corrections retained; new full regression green |149 PostgreSQL tests incl migrations; real delayed/failed SMTP continuation; public browser privacy/revocation |
| P6-005 | FIXED: coverage gets an explicit numeric block and continuity warning beside sample uptime |AnalyticsPanel regression; four-width public/detail screenshots and axe |
| P6-006 | FIXED for honest scope: maximum500 selection is explicit on counters/filter/search/sort; active incident count remains server-wide |App regression and four-width browser journey. This does not implement unbounded management pagination |
| P6-007 | FIXED: hash selection and aria-current follow the chosen section |App regression; every section at four widths |
| P6-008 | FIXED:15s deadline includes body decoding, cancellation and cleared timers |network deadline tests; existing API error/conflict tests; actual browser reconnect |
| P6-009 | Retained and broadened |Four strict viewport widths; keyboard-scrollable tables; no document overflow |
| P6-010 | MEASURED + MINIMALLY CORRECTED: expensive JIT disabled transaction-locally |Three cold/21 warm trials, one aggregate SELECT+one setting, separate EXPLAIN. Warm outlier1.180s remains a performance limitation |

Follow-up read-only frontend review found two MEDIUM regressions: dismissal while saving and lost Paused count. Both fixed with guarded dismissal/32 component tests and restored Paused/UNKNOWN counts. Follow-up reviewer found no additional actionable issue; that review did not itself run tests. Harness review corrected a vacuous post-edit check, both-client startup race, empty-incident counting, weak reconnect evidence and cleanup/report persistence. Actual rerun passed; logs separately prove295 launches/295 ends/no overlaps.

No unresolved confirmed BLOCKER/HIGH in the tested local deployment. Production limitations remain explicit in phase6-security-review.md. No full WCAG certification, exactly-once SMTP or unconditional subsecond-history claim.
