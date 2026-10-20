# ServicePulse progress — phase 4

Current checkpoint: [v0.4 maintenance/email](phase4-checkpoint.md), local gate complete; upload/CI pending.
Prior [v0.3 incidents](phase3-checkpoint.md), [v0.2 management](phase2-checkpoint.md) and v0.1 are historical.
Current branch is feat/maintenance-email-outbox, based on phase3 HEAD 3529b66.

## Completed

- Empty-workspace/environment discovery; original PDF task 3 and recruiter requirements read.
- Minimal target architecture, data/state policy, decision log and 133-ID acceptance matrix.
- API/worker/React/PostgreSQL/Alembic/simulator/Mailpit/Compose foundation and CI definition.
- Actual create → HTTP worker → persisted observation → dashboard/history vertical slice.
- SSE two-client updates and browser offline/online reconnect regression fixed and tested.
- Opt-in seed, real smoke, backend/unit/DB and frontend/component/browser tests.
- Exact master user prompt preserved; AI disclosure, essay template and review summary.
- Phase 2: versioned monitor CRUD/pause/resume/run-now, stale-work fencing and group management.
- Shared React editors, conflict-preserved drafts, recipient storage, named group SSE snapshots.
- Additive migration 0002 with actual legacy data preservation assertions and real restart test.
- Private GitHub publication of unchanged v0.1 baseline; stage uploads authorized by owner.
- Phase3: additive 0003 incidents, atomic lifecycle, administrative closures, bounded joined API,
  live filtered journal and SSE reconnect. Actual restart/lease/gap and 32s slow HTTP verified.
- Phase4: UTC maintenance CRUD/UI/SSE, event/route/address outbox, leased SMTP dispatcher/reconciliation,
  real Mailpit delivery/dedup/backoff, isolated SMTP/DB/process fault evidence and legacy migration preservation.

## In Progress

Phase4 local implementation/review verified: 107 backend, 15 component, 5 browser tests;
actual isolated SMTP/DB/acceptance-crash suite and all prior smoke scenarios passed.
Final documentation/authorized private upload and hosted CI pending. See phase4-design.md.
No phase5, PR or merge authorization inferred. Stop after completed stage4 checkpoint.

## Blocked

No local product blocker. GitHub CLI is authenticated; origin is a private repository.
Hosted CI passed for implementation 5b43b20 (run 39323301037). Exact model identifier and essay remain
submission inputs, not blockers for current implementation. No credentials belong in chat/Git.

## Next Tasks

1. Finish stage4 private upload/hosted CI, then owner reviews before requesting phase5.
2. No PR exists as of phase4 discovery. Prepared phase2/3/4 descriptions and creation commands.
3. No automatic PR/merge; chain: phase2 -> main, phase3 -> phase2, phase4 -> phase3 until bases merge.
4. Maintenance/outbox gate is now implemented; do not silently begin next phase.
5. Phase 5: remaining UI, coverage-aware uptime/charts, public projection and privacy tests.
6. Phase 6: sustained 50 monitors / 30s, actual restarts, month history benchmark and final review.
7. Phase 7: audit all pending requirements, owner essay (exactly ten sentences), approve publication.

## Verification Status

Phase4 final local: 107 PostgreSQL tests (17.83s), three legacy fixture stages + ORM check,
15 component tests, 5 real browser tests (19.1s), types/lint/format/build and npm audit zero findings.
Real isolated Mailpit/fault suite PASS (77.437s), including SMTP outage, queue/process restart, DB outage
and accepted-before-ack crash. Actual 3 physical messages/2 logical deliveries, not exactly-once SMTP.
HTTP, phase2, phase3 and forced-IP proxy regressions all rerun successfully. See phase4-checkpoint.md.

Historical phase3: 75 PostgreSQL tests (3.48s), two legacy migration fixtures/ORM check, 11 component tests,
4 browser tests (15.2s); actual restart/slow smoke PASS (73.031s). Forced different-IP proxy regression
PASS (4.563s) after fixing a discovered HIGH stale nginx upstream. Hosted CI PASS on 5b43b20:
https://github.com/azimkhanrazdva/servicepulse/actions/runs/39323301037. See phase3-checkpoint.md.

Historical phase2: 53 PostgreSQL backend tests (zero skips), legacy migration/ORM check,
9 frontend tests, 3 real browser tests, Python/ESLint/format/typecheck/build and zero npm findings.
Final live phase2 smoke PASS in 57.328s: >30s pause, manual observation, edit during HTTP,
backend/worker restart preserves settings/group with no stale or synthetic failed observations.
See artifacts/phase2-smoke.json and phase2-checkpoint.md. Hosted CI PASS on 034b4bd:
https://github.com/azimkhanrazdva/servicepulse/actions/runs/39319384324 (both jobs successful).

Historical v0.1 verification:

PASS: first HTTP smoke, initial PostgreSQL tests (26), expanded host unit tests (27 + 4 DB
skips), frontend tests (4), TypeScript, build, Python lint/format, frontend formatting,
two real Chromium E2E tests, npm audit (zero findings), seed idempotency.
Expanded DB/migration runner: PASS 31 tests, zero skips; artifacts/backend-tests.xml. Final rebuilt-image rerun: PASS 31 tests in 0.61s; final HTTP smoke PASS; final E2E 2 passed in 5.0s.

NOT VERIFIED: public privacy page, full-month history/uptime, sustained 50-monitor cadence, exhaustive fault recovery,
live external TLS and final security/product audit. Monitor/group/incident restart is verified;
outbox restart/persistence is now verified. External mailbox delivery is not claimed.

## Current Branch

`feat/maintenance-email-outbox`, descended from phase3 3529b66.
origin: https://github.com/azimkhanrazdva/servicepulse (private).
main and first-slice branch published at bd43629; no PR/merge.

## Latest Commit

Phase4 backend checkpoint: 2a159d1 — feat(notifications): add maintenance and transactional delivery outbox.
Final UI/reliability checkpoint follows this local gate; git log -1 resolves current HEAD.

Phase3 implementation: 5b43b208df112694082d8c4640c5ec012d2ca4a6 —
feat(incidents): persist lifecycle and verify scheduler recovery, 2026-10-19 20:55:01 +05:00.
Pushed to origin/feat/incident-lifecycle; hosted CI passed this exact commit.
A documentation-only handoff commit follows; `git log -1` resolves current HEAD.

Historical phase2 implementation: 034b4bda783e0a69a47d4c4875ea05fc36819e19 —
feat: add versioned monitor management and groups, 2026-10-19 20:26:42 +05:00.
Pushed to origin/feat/monitor-management-groups; hosted CI passed that exact implementation.
Current handoff documentation follows in a separate docs commit; git log -1 resolves HEAD.

Historical v0.1:

Implementation checkpoint: `4f212d959b63f590d3438c3c6ed86089069347e3` —
`feat: implement verified monitoring vertical slice`, 2026-10-19 19:51:16 +05:00, Codex Agent.
This entry belongs to a subsequent documentation commit; `git log -1 --format=fuller`
resolves current HEAD (a file cannot embed its own commit hash). No publication occurred.

## Important Context

Start date 2026-10-19; deadline 2026-10-26. P0 features before polish. Stop at the requested checkpoint.
Read AGENTS.md, requirements.md, architecture.md and development-log.md before resuming.
Groups/membership/recipients are implemented; the first-slice notes above are historical.
Incidents, maintenance and outbox are implemented; public models remain target only. Every monitor edit resets live
metrics/streak/state (PAUSED retained), history stays versioned; resume schedules UNKNOWN.
Use captured config_version for edits; stale clients get 409 and keep their drafts.
Never release an active lease on edit/pause/resume. Manual requests coalesce. Group updates
have separate versions and atomically replace membership/recipients. Local Mailpit email is now sent.
States/results/incidents now commit atomically. Pause/edit close PAUSED/CONFIG_CHANGED without recovery;
resume UNKNOWN; successful check alone closes RECOVERED. Legacy DOWN gets an incident only on a fresh
failed observation, never a historical backfill. Delete cascades incident/outbox history. Existing v0.3 incidents
have notifications disabled on 0004 upgrade; new incidents explicitly opt in. Recipients freeze at confirmation;
new addresses wait for future incidents, removal revokes pending routes. Shared addresses deduplicate per event.
Maintenance suppresses applicable routes at final authorization, never monitoring; in-flight SMTP cannot be recalled.
Uncertain acceptance retries DOWN before recovery, with possible physical duplicates. Read phase4-design.md.
UNKNOWN/UP preserve their state on the first failure; default second failure → DOWN.
History is latest 100 rows; monitor lists/SSE cap at 500. Fixed-delay cadence is completion + interval.
No synthetic results during downtime. Expiring leases fence commits; arbitrary process suspension
beyond lease expiry is a documented fault-model limit, not an absolute non-overlap guarantee.
Private targets are blocked unless origin exactly matches configured simulator service/port.
All published ports bind loopback. .env is ignored, only disposable test defaults are tracked.
Screenshots are actual browser captures in output/playwright; tests remove only their own monitors.
Demo setup leaves two real monitors for owner inspection; repeated seed adds no duplicates.
