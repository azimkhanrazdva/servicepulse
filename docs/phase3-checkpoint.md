# Phase 3 — incident lifecycle checkpoint

Implementation: additive Alembic 0003, durable incident UUIDs and database-enforced single open incident,
atomic monitor/result/lifecycle completion, recovery and administrative closure, filtered/paginated API,
live journal with durations and existing SSE reconnect. No new runtime dependency/infrastructure.
See architecture.md and ADR-009/010 for exact semantics and migration policy.

## Verification

- Baseline: 53 PostgreSQL tests and 9 component tests passed before changes.
- Expanded PostgreSQL suite: 75 passed in 4.12s; 0001 UP and 0002 DOWN/group/recipient fixtures survive
  upgrade to 0003; Alembic metadata check passed. Final rebuilt normal command: 75 passed in 3.48s.
- Frontend: 11 tests, typecheck, ESLint, formatting and build passed; npm audit zero findings.
- Playwright final: 4 passed in 15.2s, including original tests, real threshold/recovery/two-client journal,
  ticking duration and offline/online full resynchronization. artifacts/browser-tests.json.
- Live Docker smoke final: PASS in 73.031s (initial run 57.453s); artifacts/phase3-smoke.json. A cancelled HTTP and stopped worker
  leave no result; lease recovery after backend/worker restart preserves incident identity/settings.
  Further failures keep one incident; success closes it once. Real 32s HTTP exceeds 30s interval,
  cannot be manually relaunched, produces one result, and a fast monitor completes during it.
- SQL rollback test deliberately executes SELECT 1/0 after lifecycle flush: state/result/incident all
  roll back and expired lease can recover. API page test verifies one JOIN for 100/150 incidents.
- Existing mutation race tests now run with both successful and failed stale HTTP; no result/incident
  survives edit/pause/delete/pause-resume. Competing workers' claims are disjoint; completion retry
  commits once; an expired old success cannot close a newer incident.
- Found/fixed HIGH: nginx kept a replaced backend's old IP, causing 3 browser failures/1 pass. Docker
  DNS resolution now refreshes every 2s. Deterministic different-IP replacement smoke passed in 4.563s,
  with frontend container unchanged; artifacts/proxy-recreate.json, nginx -t PASS, final browser suite PASS.

Commands: docker compose --profile test run --rm tests; ruff check/format --check backend;
npm test; npm run typecheck/lint/format:check/build/test:e2e; npm audit --audit-level=high;
docker compose up -d --build; python scripts/phase3_smoke.py. Mounted development commands explicitly
set PYTHONPATH=/app to avoid old installed-code/new-source mismatch; final gate uses rebuilt images.
Proxy regression command: python scripts/proxy_recreate_smoke.py (replaces only the backend container,
reserves its old address temporarily and removes its own holder; does not delete the database volume).

## Honest limits

No SMTP/outbox/maintenance/public projection/charts/uptime/month benchmark or sustained 50-monitor
load evidence yet. Arbitrary process suspension beyond lease expiry can overlap physical HTTP;
UUID fencing rejects old commits, not requests already in progress. Offset pagination can shift
under concurrent inserts; filter by time for deep history. This is an implementation-agent critical
review, not an independent reviewer. No stage3 PR/merge authorized or created.

Branch feat/incident-lifecycle starts at phase2 3569b1c; main still authentic v0.1 bd43629.
Implementation 5b43b208df112694082d8c4640c5ec012d2ca4a6 was uploaded under the owner's existing
authorization. Hosted CI PASS for that exact SHA: backend 37s, frontend 28s, run
https://github.com/azimkhanrazdva/servicepulse/actions/runs/39323301037.
Raw artifacts/github-ci-phase3.json and consolidated artifacts/phase3-checkpoint.json preserve evidence.
A later documentation-only commit records the result; no product logic changes after this gate.
Repo remains private. Stop for owner review.
