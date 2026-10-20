# Phase6 first verified increment — reliability and measured baseline

**PARTIAL Phase6; not v0.6 release approval.** Existing application version remains0.5 while
the requested audit/reliability/monochrome phase proceeds. This safe checkpoint finishes the
critical backend increment; all unfinished phase work stays local. No autonomous continuation
after ending a session, no Phase7/submission/remote PR/merge/public visibility action.

Started clean4696798 on2026-10-20, branch feat/reliability-audit-redesign. Actual source request:
prompts/006-audit-reliability-redesign.md. See phase6-audit.md for ten confirmed findings,
independent agent review provenance and original employer behavior mapping.

## Implemented and verified

- Additive0006 preserves required new DOWN outside maintenance despite quick recovery/offline
  dispatcher, followed by ordered RECOVERY. Eligibility/deadline survives restart, is independent
  of SMTP attempt markers, and accounts for maintenance edits and shared group routes.
- Wholly maintained outage stays silent; recovery uses HTTP completion timestamp even when
  persistence is delayed. Final recipient-route removal terminally revokes pending deliveries
  for both open and recovered incidents; re-addition cannot revive them. Delivery rows are locked
  under monitor parents during policy mutation. Legacy unknown eligibility is not guessed.
- Expired worker claim cannot start HTTP. Valid preflight refreshes the full timeout+15s budget
  after row-lock wait; arbitrary suspension beyond a lease remains outside the guarantee.
- Public freshness aggregation ignores PAUSED; health/freshness remain distinct. Analytics SQL
  retained, with new manual-burst/same-time/legacy/end-boundary coverage tests.
- Host allowlist at management ASGI and nginx; actual normal200/hostile400 on8000/8080.
- Strict390px mobile overflow reproduced and fixed with wrapped labelled navigation; all four
  requested viewport widths render50 actual load monitors without document overflow.
- Real mixed50x30 five-minute run repeated after correcting omitted worker resource samples.
  Latest475 persisted observations, max41 active HTTP calls, no same-monitor overlaps; raw proof
  includes timings/CPU/RAM. This is not the unperformed50-monitor fault matrix.
- Synthetic history benchmark10k/100k/500k/1m across50 plus100k one-monitor, plans/sizes/first/warm
  timings. Warm dense p95~609ms; first1.143s is an explicit remaining performance risk.

## Actual local verification

| Check | Result / source |
| --- | --- |
| All backend + PostgreSQL |148 PASS,0fail/skip,29.69s; artifacts/backend-tests.xml |
| Migration fixtures |0001/2/3/4 plus explicit0005 publication/cadence ->0006 preserved; alembic check no new operations |
| Component |26 PASS; artifacts/frontend-tests.json |
| Browser |7 PASS,19.1s; all original cases retained, strict viewport strengthened; artifacts/browser-tests.json |
| Ruff /format /TypeScript /ESLint /Prettier /production build |PASS; actual commands in development-log.md |
| Real slice /phase2 /phase3 /proxy replacement |PASS,0.641/57.281/57.578/6.641s; actual reports retained |
| Real new SMTP offline/retry/restart |PASS,52.0s; artifacts/phase6-email-smoke.json |
| Existing seven live fault groups |PASS,93.14s; artifacts/phase4-fault.json; physical3/logical2 acceptance crash |
| Sustained load |PASS measured steady scope; artifacts/phase6-load*.json/jsonl |
| Month benchmark |PASS execution/counts/plans; first-call<1s NOT SATISFIED; phase6-history-benchmark.json |
| Host guard |8 actual GET assertions PASS; phase6-host-guard.json |
| Dependency audits |npm0 known vulnerabilities; pip-audit pinned requirements0 known vulnerabilities; phase6-*-audit.json |
| History secret patterns |0 matching private-key/GitHub/AWS patterns; .env untracked; narrow scan, not a complete secret guarantee |
| Hosted CI for Phase6 |NOT VERIFIED: phase unfinished/local, not uploaded |

Current Phase5 exact HEAD Actions39390995802 rechecked SUCCESS; it proves baseline4696798,
not these new changes. Never reuse it as Phase6 CI proof. Real local commits follow verification;
use git log for their exact hashes and timestamps without a self-referential current hash here.

## Precise continuation

1. Read AGENTS, requirements, progress, phase6-audit, phase6-notification-policy and performance.
2. Stay on current branch; check clean status/last commits. Do not branch from stale main or
   rewrite0001..0005/history;0006 is the new additive migration.
3. Finish P0: isolated fault-under50 matrix and missing end-boundary schedule accounting;
   repeat dense first-query budget and evaluate measured sort/materialization cost. Do not
   turn warm-only success into universal month latency. Full security/acceptance pass remains.
4. Implement P1 monochrome redesign in existing React/CSS. Resolve P6-005..008 and requested
   filters/dialogs/delivery diagnostics/copy/preview, honest<=500 scope and paired uptime/coverage.
   Reuse real APIs/public isolation, avoid a third conflicting global stylesheet or heavy UI dependency.
5. Four viewports, keyboard-only journey/focus/Escape, automatic accessibility, actual screenshots
   and public/admin complete user journeys. Baseline images are not final redesign evidence.
6. Complete full regression, update docs/matrix/log, review/stage/secret checks, logical commits.
   Only after full verified Phase6 may standing authorization push privately and verify exact CI.
   Prepare PRs; creating new remote PRs/merge/visibility change requires owner authorization.

Main stack remains available: admin8080,API8000,public8081/status/{owner-slug},Mailpit8025.
No default public listing/page; tests remove only their own resource IDs. All isolated performance/
benchmark/email/fault volumes were removed under their explicit test project names, never main DB.
No owner essay/model identity or final submission is invented. Roadmap dates are future plans.
