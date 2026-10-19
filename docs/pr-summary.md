# Proposed PR — first vertical slice

No remote repository or PR has been created. This is a local review summary.

## Problem and result

An empty workspace needed a reproducible first monitoring path. The application now creates
a monitor through React or FastAPI, lets a separate async worker check an actual simulator,
stores the observation in PostgreSQL and displays state/code/latency/history through SSE.

## Implementation

- Independent API, worker, frontend, DB, simulator and Mailpit Compose services.
- Explicit Alembic migration with constraints and scheduling/history indexes.
- Fenced PostgreSQL claims; configurable checks and two-failure state confirmation.
- Narrow simulator exception plus DNS/IP/redirect/timeout/body protections.
- Unit, isolated DB, real HTTP smoke and two-client browser verification.
- English README, source-derived acceptance matrix, prompt/development/decision evidence.

## Validation

Refer to artifacts/backend-tests.xml, artifacts/browser-tests.json, artifacts/smoke.json,
artifacts/npm-audit.json and docs/development-log.md for actual current results.
Hosted GitHub Actions has not run. No 50-monitor load or monthly-history benchmark is claimed.

## Explicit next scope

Edit/pause/resume, groups, incidents, transactional email outbox, maintenance, remaining
screens, uptime/charts and public privacy projection. No publication or merge in this checkpoint.
