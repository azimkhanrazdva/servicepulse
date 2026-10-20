# Phase 4 — maintenance and email checkpoint

Implementation verified locally, uploaded privately and passed hosted CI on exact SHA ade9c13.
Branch: feat/maintenance-email-outbox, based on phase3 documentation HEAD 3529b66.
First backend checkpoint: 2a159d1, feat(notifications): add maintenance and transactional delivery outbox.
Final UI/reliability implementation: ade9c13b470dc02a9437d488b724b7a05eb54417, created at
2026-10-20T06:21:35+05:00. Hosted CI: backend 47s, frontend 21s, both successful:
https://github.com/azimkhanrazdva/servicepulse/actions/runs/39379923079.
Raw result: artifacts/github-ci-phase4.json; consolidated actual reports: artifacts/phase4-checkpoint.json.
Later documentation-only handoff records these outcomes without product logic changes.

## Implemented

- Additive 0004 maintenance/event/route/delivery schema, bounds/unique constraints/indexes and legacy opt-in policy.
- Monitor/group versioned maintenance CRUD; UTC validation, exclusive target, overlap semantics and target cascades.
- Existing monitoring state/result/incident transaction now includes durable DOWN/RECOVERY events and frozen routing.
- One delivery per normalized email/event across groups; current recipients/membership revalidated before attempts.
- Separate dispatcher with fenced leases, finite backoff, permanent-error categories, bounded logging and reconciliation.
- Local SMTP acceptance via Mailpit, delivery-state diagnostic API, no external credentials or provider requirement.
- Functional React maintenance editor/list/filter/pagination, direct group/monitor badges, timezone disclosure,
  draft-preserving 409 handling and SSE reconnect without stale refresh-error messages.
- Existing incidents migrated with notifications_enabled=false; no invented events or bulk old alerts.

API: GET/POST /api/maintenance; PUT/DELETE /api/maintenance/{id} with config_version;
GET state=ACTIVE|UPCOMING|ENDED, limit<=100/offset<=10000. GET /api/notifications supports incident_id,
limit/offset and only bounded delivery diagnostics. Named maintenance SSE includes active target IDs.

## Executed evidence

- Baseline 75 backend/11 component tests passed before changes.
- Final rebuilt-image backend command: **107 passed in 17.83s**, zero skips. All three legacy fixture
  stages (0001,0002,0003) preserve actual values through 0004; Alembic metadata check PASS.
- Frontend **15 passed**, types/ESLint/Prettier/build PASS, npm audit zero findings.
- Browser integration initially 4 passed + maintenance timeout; trace showed exact label selection did
  not match a recreated native select. Switched to its observed combobox role; single new case passed
  in 18.4s, then full 5 passed in 18.0s. After fixing stale reconnect load errors, final rebuilt UI:
  **5 passed in 19.1s**, with a specific assertion that the recovered refresh error disappears.
- Isolated real fault suite **PASS in 77.437s**, artifacts/phase4-fault.json and bounded phase4-fault.log.
  Real SMTP/API verified DOWN→RECOVERY, shared-address dedup, repeated failures, group/monitor maintenance,
  continued checks/real DOWN, window-end release without new results, deferred recovery, and no stale pair.
  Stopped/restarted Mailpit, dispatcher/worker, and PostgreSQL in its own project; retry retained its delivery ID.
  Crash helper exited after DATA acceptance before DB ack: **3 physical emails, 2 logical deliveries**,
  preserving DOWN-before-RECOVERY after expired lease recovery. Temporary project/volume cleaned up.
- HTTP smoke PASS (0.609s); phase2 restart/pause/edit smoke PASS (56.953s); phase3 incident/32s target
  smoke PASS (57.813s); forced different-IP nginx regression PASS (8.984s). Reports contain latest real times.
- Added deterministic tests for monitor-wide multi-group suppression, claim-time revalidation, exact start/end,
  cancellation/reclaim and a pause completing while SMTP is in flight (no monitor transaction held).

Commands: docker compose up -d --build; docker compose --profile test run --rm --build tests;
ruff check/format --check backend; npm test; npm run typecheck/lint/format:check/build/test:e2e;
npm audit --audit-level=high; python scripts/smoke.py; phase2_smoke.py; phase3_smoke.py;
proxy_recreate_smoke.py; phase4_fault_smoke.py. The latter exclusively uses servicepulse-phase4-fault,
ports 18000/18025 and its own disposable volume, never the application's data volume.

## Delivery guarantees and remaining limits

Contract: phase4-design.md, ADR-011..013. No SMTP network call inside a monitoring/database transaction.
Suppression is checked at persisted authorization; maintenance/changes after that cannot recall SMTP in flight.
Logical event/delivery IDs are unique. Physical exactly-once and eventual mailbox delivery are not promised;
retry exhaustion requires investigation. Case-insensitive address normalization is an explicit local-catcher policy.
Recipients are frozen at confirmation; additions wait for future incidents, removals revoke unsent routes.
Public page, uptime/charts, sustained 50-monitor benchmark and final full security review remain later phases.
No PR/merge or public publication performed. Stop for owner review after this stage's verified upload.
