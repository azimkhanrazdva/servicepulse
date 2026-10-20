# ServicePulse progress — Phase6 first reliability checkpoint (PARTIAL)

Read AGENTS.md, requirements.md, architecture.md, phase6-audit.md,
phase6-notification-policy.md, phase6-performance.md and phase6-checkpoint.md before resuming.
Application version remains0.5; the complete requested v0.6 redesign/audit is NOT finished.

## Completed

- Prior verified phases1–5 preserved; no original commit/date or migration0001..0005 rewritten.
- New branch feat/reliability-audit-redesign from clean4696798 after actual Git/PR/CI discovery.
- Three independent read-only agent reviews; original PDF task3 re-extracted; ten actual findings.
- Reproduced email/lease/public defects before fixes (4FAIL/8PASS artifact), then corrected them.
- Additive0006 persisted notification eligibility/obligation; actual ordered delayed-DOWN/recovery,
  maintenance-only suppression, permanent route revocation including recovered pending events,
  observation-vs-persistence time and existing retry/crash boundaries verified.
- Expired worker claim guarded; valid lease budget refreshed; PAUSED public freshness corrected.
- Management Host guards, actual200/400 API/nginx tests; zero known npm/pinned-Python audit findings.
- Two actual five-minute50x30 experiments; corrected missing worker resource collection and reran.
  Latest475 actual HTTP/results,375success/100failure, max41, no measured overlaps; CPU/RAM recorded.
- Synthetic monthly10k/100k/500k/1m fleet plus100k single-monitor, repeated percentiles/plans/sizes.
  Warm dense p95~609ms; first1.143s remains a performance budget risk, not hidden.
- Strict390px overflow reproduced/fixed; four requested widths render50 real rows without document overflow.
- Current local gates148 backend,26 component,7 real browser; migration preservation through0006;
  current actual SMTP/restart/crash/small-fleet/proxy regressions passed. See checkpoint and log.

## In Progress

Phase6 remains PARTIAL. First safe backend/performance/mobile correction increment is verified
locally and recorded in real local logical commits. Full monochrome redesign, accessibility,
fault-under50 and final acceptance are unfinished. No Phase7 work or full-release claim.

## Blocked

No owner action needed for ordinary remaining development. Remaining acceptance gaps are work,
not external blockers: dense first-query budget, full50-monitor fault matrix/end-boundary counters,
P6-005..008 UX issues, complete monochrome/accessibility/final-security/CI gates.
Legacy queued deliveries have unknown historical eligibility; no guessed upgrade mass-mailing.
Exact model identifier, personal ten-sentence essay and final employer access remain owner inputs later.

## Next Tasks

1. Confirm clean branch/log; read phase6-checkpoint precise continuation. Do not branch from main.
2. Finish P0 isolated fault-under50 and complete planned/missed boundary accounting; repeat/analyze
   dense first-call latency (external sorts/temp blocks) before an unconditional<1s claim.
3. Finish security/acceptance review; Host/SSRF/privacy/dependency tests already have actual evidence.
4. Apply requested unified white/black redesign in existing React/CSS, resolve coverage prominence,
   honest500 scope, active navigation, request deadlines, filters/dialogs/diagnostics/copy/preview.
5. Four viewport/keyboard/focus/Escape/automatic accessibility/visual/public+admin user journeys.
6. Full final regression, docs/matrix/log/review/commits; only completed verified Phase6 can be
   privately pushed under standing authorization, followed by exact-head hosted CI verification.
7. Prepare new remote PR creation for owner approval; no automatic PR/merge/visibility change.

## Verification Status

PASS local:148 backend,0failure/skip; legacy0001/2/3/4/5 fixtures ->0006, Alembic check;
26component,7Chromium, Ruff/format/TypeScript/ESLint/Prettier/build; actualSMTP/fault/restart/proxy.
PASS measured steady50x30:475HTTP/results,300s, max41, scheduler steady p95~0.552s.
PASS synthetic benchmark execution/counts/plans; warm p95<1s. First dense1.143s >target:PARTIAL.
PASS dependency audit0known vulnerabilities and limited secret-pattern scan; not a complete guarantee.
NOT VERIFIED: full redesign/a11y,50-fault matrix, final whole-product security/acceptance, Phase6 CI.
Baseline4696798 hosted Actions39390995802 is SUCCESS; never call it CI evidence for new local commits.

## Current Branch

feat/reliability-audit-redesign, parent4696798247feec3dab6642555cfc8794e417bfc9.
Private origin unchanged. Existing PR#1 phase2->main,#2 phase3->phase2,#3 phase4->phase3.
No Phase5/6 remote PR created; summaries prepared. No Phase6 upload while stage unfinished.

## Latest Commit

Run git log -3 --format=fuller for actual local checkpoint commits. This file is committed with
its handoff and does not fabricate a self-referential HEAD hash. Development log records real hashes.

## Important Context

Main DB/user configuration preserved; main stack8080/API8000/public8081/Mailpit8025 remains running.
No automatic publication or public root; owner chooses page/slug/labels/history, then /status/{slug}.
Isolated performance/benchmark/email/fault projects were removed only by their explicit project names.
Do not use main compose down -v. Tests create/delete only their own IDs; disposable test-db can stop.
SMTP physical duplicates remain possible after acceptance-before-ack crash; retry exhaustion is finite.
Missing observations never become DOWN; sample uptime is distinct from observed coverage.
Keep compatibility/public isolation/no arbitrary private targets; explicit narrow simulator exception.
