# feat: initialize ServicePulse and implement first vertical slice

Prepared first-PR description. Private repository now exists at
https://github.com/azimkhanrazdva/servicepulse; no PR has been created.
main and feat/first-vertical-slice share bd43629, so they have no meaningful PR diff.
See github-workflow.md for the preserved-history baseline decision.

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
For v0.1 evidence use those files at bd43629: 31 backend tests, 4 frontend tests, 2 browser
tests and real HTTP smoke passed; Python lint/format, TypeScript/build/format passed; npm audit zero.
Later feature-branch artifacts are newer evidence, not retroactive v0.1 measurements.
Hosted GitHub Actions has not run. No 50-monitor load or monthly-history benchmark is claimed.

## Explicit next scope

Edit/pause/resume, groups, incidents, transactional email outbox, maintenance, remaining
screens, uptime/charts and public privacy projection were outside v0.1. Its baseline is now
published privately; no remote PR or merge was performed.

## Architecture decisions and authentic commits

FastAPI/Python 3.12, SQLAlchemy/Alembic/PostgreSQL, independent bounded async worker,
React/TypeScript/Vite/nginx. PostgreSQL leases keep scheduling durable without Redis;
SSE snapshots support independent clients/reconnect; validated IP connections bound SSRF.
SMTP remains Mailpit-only infrastructure; monthly history and load tests are pending.

- 4f212d959b63f590d3438c3c6ed86089069347e3 — feat: implement verified monitoring vertical slice.
- bd4362991d1b74e52b46fa35d53cb04fb9f38835 — docs: record verified checkpoint and continuation.
- Development log: [docs/development-log.md](development-log.md).
