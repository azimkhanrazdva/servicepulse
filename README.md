# ServicePulse

A website availability monitoring platform built for Mad Devs' Junior Agentic Developer
take-home assignment #3. **Version 0.4 adds maintenance windows and transactional email delivery through Mailpit. Public status and uptime analytics remain pending.**

Create a monitor, let an independent worker request a real HTTP target, persist observations
in PostgreSQL and see the dashboard update through SSE. No fabricated metrics or HTTP results.

## Current features

- Create/edit/delete/pause/resume/run-now through React and API; configurable interval, timeout, status, body match and confirmation threshold.
- Versioned edits with explicit conflict recovery; active HTTP leases survive changes and stale results are discarded.
- Group CRUD, many-to-many membership, aggregate status and validated per-group email recipients.
- Monitor/group maintenance CRUD, overlapping-window suppression and independent post-window reconciliation.
- Transactional event/route/per-address outbox, shared-recipient deduplication, SMTP retries and delivery diagnostics.
- Separate asynchronous worker with bounded concurrency, durable scheduling, fenced database leases.
- UNKNOWN → UP/DOWN state with two consecutive failures by default; manual run queue.
- Atomic incident lifecycle, one open incident per monitor, recovery and distinct administrative closures.
- Filtered/paginated incident API and live journal with ticking durations and two-client reconnect.
- Dark responsive React dashboard, real HTTP code/latency/timestamps and recent observation history.
- SSE snapshots and automatic browser reconnect; full resynchronization on the next snapshot.
- Alembic migration, isolated PostgreSQL integration tests, HTTP simulator and Mailpit container.
- URL/DNS destination policy, pinned numeric connections, no redirects/proxies, bounded response/time.

**Not implemented:** public status page, uptime aggregates, response charts, monthly history endpoint.
Actual SMTP/Mailpit tests and failure evidence are in [phase 4 checkpoint](docs/phase4-checkpoint.md).
The whole assignment is not yet complete. See [acceptance matrix](docs/requirements.md).

## Architecture and stack

React 19 + TypeScript + Vite → nginx same-origin proxy → FastAPI → PostgreSQL 17.
A separate Python 3.12 worker claims work in PostgreSQL and uses asynchronous HTTPX.
A separate SMTP dispatcher processes durable notification deliveries and reconciles maintenance.
SQLAlchemy 2 and Alembic manage persistence. No Redis, Celery or distributed broker.
SSE sends full snapshots every two seconds; small-scale database polling is intentional.

See [architecture](docs/architecture.md) and [decisions](docs/decisions.md) for models,
state/incident policy, implemented outbox design, alternatives and limitations.

```text
backend/       FastAPI, checker, worker, SQLAlchemy, Alembic, pytest
frontend/      React console, Vitest tests, Playwright E2E, nginx
simulator/     Controllable local HTTP targets
scripts/       Real smoke test and idempotent opt-in demo setup
docs/          Requirements, decisions, progress, actual prompts and development history
artifacts/     Machine-readable verification evidence
compose.yaml   Local application and isolated test profile
```

## Prerequisites and local startup

Docker Engine/Desktop with Linux containers and Docker Compose v2+; free localhost ports
8080 (UI), 8000 (API), 8025 (Mailpit). Initial image/dependency download needs internet.
Windows PowerShell, macOS and Linux are supported by Compose; development was verified on
Windows with Docker Desktop. Python 3.11+ is only required for host smoke/seed scripts.

PowerShell preparation (once):

```powershell
Copy-Item .env.example .env
```

macOS/Linux preparation: `cp .env.example .env`. Then the same startup command everywhere:

```sh
docker compose up -d --build
```

Migration runs once before API and worker startup. The database uses a persistent named volume.
Open [dashboard](http://localhost:8080), [OpenAPI docs](http://localhost:8000/docs),
[Mailpit](http://localhost:8025). `docker compose ps --all` shows readiness/migration state.
Stop with `docker compose stop`; start again with `docker compose up -d`.
Do not remove the database volume if you need to retain observations.

Management has no login and is intended for a trusted local machine. All published ports bind
to 127.0.0.1. Do not expose the management API to an untrusted network.

## Configuration

| Variable | Default | Meaning |
|---|---|---|
| POSTGRES_DB | servicepulse | Compose database name |
| POSTGRES_USER | servicepulse | Disposable local DB user |
| POSTGRES_PASSWORD | local-development-only | Disposable local value; never reuse elsewhere |
| DATABASE_URL | Compose-generated | SQLAlchemy asyncpg DSN; host development can override |
| SIMULATOR_ORIGIN | empty in code/Compose | Exact test-only private target origin; .env.example opts into http://simulator:8090 |
| CONCURRENCY | 50 | Worker task/connection cap, range 1..100 |
| MAX_BODY_BYTES | 1048576 | Stream body limit, max 10 MiB |
| SMTP_HOST | mailpit | Local catcher hostname; no external provider required |
| SMTP_PORT | 1025 | Internal SMTP port |
| SMTP_SENDER | servicepulse@example.com | Disposable local sender |
| SMTP_TIMEOUT_SECONDS | 5 | SMTP socket-operation timeout, 0.1..10s |

`CONCURRENCY` and `MAX_BODY_BYTES` are application environment variables; add them explicitly
under the shared backend environment in Compose to override defaults. `.env` is ignored.
There are no real keys or SMTP credentials in the repository. SMTP acceptance is captured locally;
no external mailbox delivery is claimed. This phase has no authenticated/TLS provider integration.

## Simulator and demonstration

The simulator is internal to the Compose network. In the UI create a monitor named `Demo API`
with URL `http://simulator:8090/target/api`; expected status 200, body `ServicePulse ready`.
The opt-in exact origin in `.env` permits only this service/port; arbitrary internal URLs remain blocked.
For reproducible configuration-only demo seed:

```sh
python scripts/seed.py
python scripts/smoke.py
```

Seed creates two monitors without fake observations. Smoke creates its own uniquely named
monitor, waits up to 20s for worker success, verifies saved history and manual queue, deletes
only its own monitor, and writes `artifacts/smoke.json` (including failures).

Set a target to return an error (Python standard library inside the API container):

```sh
docker compose exec backend python -c "import urllib.request; req=urllib.request.Request('http://simulator:8090/control/api', data=b'{\"status\":500}', headers={'Content-Type':'application/json'}, method='PUT'); print(urllib.request.urlopen(req).status)"
```

The same PUT JSON accepts `status` (200..599), `delay` (0..180s), `body` and `redirect`.
Use `status:200` to recover, `delay:10` with a 5s monitor timeout for timeout behavior,
404/500 for status failures, and changed text for body mismatch. Control state is in-memory,
reset on simulator restart. Disconnect simulation is not implemented; delay exceeds client
deadline instead. Run now twice after failures to cross the default threshold, then recover.
This changes real monitor state and incident records at the configured threshold. Put the monitor in a
group with a disposable recipient to receive DOWN, then RECOVERY, in Mailpit. Repeated failed checks
produce no additional normal-path DOWN. Mailpit captures messages; it does not forward them externally.

For maintenance, open the Maintenance section, choose a monitor or group, enter local start/end time,
and save. The UI names your timezone; PostgreSQL stores UTC. Checks and DOWN continue with a separate
MAINTENANCE badge. A monitor window suppresses all routes; a group window suppresses only its group.
When the final applicable window ends, DOWN can send without waiting for another HTTP check. Recovery
entirely inside a window produces no stale pair if DOWN had not been attempted. See the delivery contract below.

## API

| Method | Path | Behavior |
|---|---|---|
| GET | /api/health | Process liveness |
| GET | /api/ready | Database/schema readiness |
| GET / POST | /api/monitors | List (max 500) / create |
| GET / PUT / DELETE | /api/monitors/{uuid} | Read / replace config with version / delete with optional version |
| POST | /api/monitors/{uuid}/pause or /resume | Version-guarded state action; resume schedules immediately |
| POST | /api/monitors/{uuid}/run | Queue check; 409 if already leased/paused |
| GET | /api/monitors/{uuid}/results | Most recent 100 observations |
| GET / POST | /api/groups | List / create group with members and recipients |
| GET | /api/incidents | Filtered journal; state, monitor_id, since/until, order, limit, offset |
| GET | /api/incidents/active | Paginated open incidents |
| GET | /api/incidents/{uuid} | Incident detail |
| GET | /api/monitors/{uuid}/incidents | Per-monitor journal |
| GET / PUT / DELETE | /api/groups/{uuid} | Read / versioned replacement / versioned deletion |
| GET / POST | /api/maintenance | Paginated list / create monitor or group window |
| PUT / DELETE | /api/maintenance/{uuid} | Versioned replacement / versioned deletion |
| GET | /api/notifications | Bounded diagnostic deliveries; optional incident_id, limit, offset |
| GET | /api/events | Monitor array + named groups/incidents/maintenance events from one DB snapshot every 2 seconds |

FastAPI publishes schemas and example requests at `/docs`. Invalid input returns 422;
missing monitor/group 404. PUT and pause/resume require config_version; stale versions return 409.
Browser deletes include config_version in the query; unversioned monitor DELETE remains compatible
with v0.1 scripts and is unconditional. Group DELETE always requires a version. URL syntax is checked on input; DNS destination policy is enforced at
execution to account for changing DNS. A blocked destination records a bounded failure reason.

## Testing

Run all backend tests against a **separate temporary PostgreSQL**, including migrations:

```sh
docker compose --profile test run --rm --build tests
```

The profile's `test-db` uses tmpfs and a dedicated `servicepulse_test` database. Tests refuse
to reset a database whose name differs or whose two configured URLs do not match. The runner
clears only test tables/migration metadata, applies Alembic from scratch, checks ORM/schema
agreement and runs pytest. The runner inserts a legacy monitor/result at migration 0001 and
asserts their settings, IDs, state and history survive upgrades. A second fixture at 0002 verifies a DOWN
monitor/result/group/recipient survive 0003 without fictional incident backfill. This never resets the application's `db` volume.
The 0003 fixture additionally preserves actual open/closed incidents byte-for-value through 0004;
their notifications_enabled remains false and no historical email events are created.

Host development (optional):

```sh
python -m venv .venv
# Activate .venv using your shell, then:
pip install -r backend/requirements.lock
pip install --no-deps -e backend
ruff check backend
ruff format --check backend
pytest backend/tests -q
cd frontend
npm ci
npm test
npm run typecheck
npm run lint
npm run format:check
npm run build
npx playwright install chromium
npm run test:e2e
```

Without `TEST_DATABASE_URL`, host pytest deliberately skips DB tests. Use the Compose test
command for full backend evidence. Browser tests require the running Compose application;
they retain the original real-form/worker/two-context/reconnect checks and add edit conflicts,
pause/resume, Run Now, confirmed deletion, membership filtering and group recipient management.
Screenshots are written to `output/playwright/`; machine report is `artifacts/browser-tests.json`.
Actual browser captures (updated by the latest test run): [desktop](output/playwright/desktop.png) and
[mobile](output/playwright/mobile.png). Current phase: [management checkpoint](docs/phase2-checkpoint.md).
Current incident checkpoint: [phase 3](docs/phase3-checkpoint.md). `python scripts/phase3_smoke.py`
verifies actual incident/restart/gap behavior and a 32s target across its 30s interval.
`python scripts/proxy_recreate_smoke.py` verifies nginx recovers after backend replacement at a new IP.
Phase4 live fault suite: `python scripts/phase4_fault_smoke.py`. It creates a separate Compose project,
ports 18000/18025 and its own DB volume; tests SMTP outage, restart, DB outage and acceptance-before-ack
crash, then removes only that isolated project/volume. Leave these ports free. Evidence is in
artifacts/phase4-fault.json and phase4-fault.log. Browser integration also checks actual Mailpit receipts.
On restricted Windows execution, local socket access and launching Chromium may require
host permission. A sandbox denial is not proof of an application failure or passing test.

GitHub Actions specifies Python lint/format/PostgreSQL tests and frontend format/tests/types/build.
Hosted CI **passed** for v0.4 implementation ade9c13, including actual SMTP/Mailpit integration:
[actual Actions run](https://github.com/azimkhanrazdva/servicepulse/actions/runs/39379923079).
Both backend and frontend jobs completed successfully. Later handoff documentation does not alter code.
Private repository: https://github.com/azimkhanrazdva/servicepulse. main records v0.1;
feat/monitor-management-groups carries v0.2; feat/incident-lifecycle v0.3;
feat/maintenance-email-outbox carries verified v0.4. Open review chain:
[phase 2 PR #1](https://github.com/azimkhanrazdva/servicepulse/pull/1) →
[phase 3 PR #2](https://github.com/azimkhanrazdva/servicepulse/pull/2) →
[phase 4 PR #3](https://github.com/azimkhanrazdva/servicepulse/pull/3). No merge has been performed.
See [GitHub workflow](docs/github-workflow.md) for the authentic baseline and publication policy.

## Management semantics

Editing any monitor field resets current metrics/streak and UNKNOWN state, retaining historical
observations with their config_version; paused monitors stay PAUSED. Old HTTP work keeps its lease
until completion/expiry and cannot commit stale observations. Resume sets UNKNOWN and schedules now.
Two same-version edits cannot silently overwrite each other: the loser gets 409, keeps its draft,
and explicitly discards/reloads before retrying. Name-only edits follow the same reset policy.

Groups ignore PAUSED members, then choose DOWN over UNKNOWN over UP. All paused gives PAUSED;
empty gives UNKNOWN. Membership and recipient replacement is atomic; deleting a group keeps monitors.
Recipients are syntactically validated; delivery addresses are case-normalized and deduplicated across
groups. SMTP alerts are now sent through the local Mailpit catcher.

## Delivery and maintenance contract

Logical events are unique (incident UUID, DOWN/RECOVERY). Frozen group routes are captured at confirmation;
one delivery is unique (event UUID, normalized email), even when that address belongs to multiple groups.
New recipients/groups apply to future incidents; removed recipients/membership revoke pending routes.
Any eligible group can authorize a shared address. Monitor maintenance blocks every route; group maintenance
blocks that group only. Windows use start <= now < end, and overlaps remain effective until all applicable
windows have ended. A two-second reconciliation tick advances persisted work without fabricated observations.

SMTP runs outside monitoring/database transactions. Each attempt revalidates routes/windows and persists
authorization immediately before sending. A window/settings change after that point cannot recall SMTP
already in flight. This boundary is documented/tested, rather than claiming an impossible atomic SMTP/DB operation.

Queued unattempted DOWN is cancelled on recovery; no pointless RECOVERY follows. If DOWN was accepted,
RECOVERY waits through maintenance and sends afterward. Uncertain acceptance after crash/timeout retries
the previously authorized DOWN before RECOVERY; physical duplication is possible. Known rejection clears
that authorization. PAUSED/CONFIG_CHANGED never generates recovery; pending old DOWN is cancelled on preflight.
Existing incidents at migration 0004 are excluded from alerts, avoiding historical backfill/mass mail.

Claims use persisted leases/UUID fences. Temporary failures back off 5..300 seconds, at most eight attempts;
permanent rejection or exhaustion is FAILED and requires investigation. Logical creation/dedup is database
enforced. Delivery attempts are at least once within this retry policy; SMTP acceptance does not prove mailbox
delivery. The actual crash experiment produced **3 physical messages for 2 logical deliveries**, preserving
DOWN-before-RECOVERY order. Stable Message-ID helps diagnosis but cannot promise receiver deduplication.
Full rules and error categories: [phase4 design](docs/phase4-design.md).

Incidents open at threshold confirmation and recover on a successful observation. Pause closes PAUSED;
any edit closes CONFIG_CHANGED, including name-only edits under the existing reset policy. Those closures
have no recovered_at. Deletion cascades incident history. Legacy DOWN rows keep their settings/state;
only a new failed observation starts tracked history, and unknown pre-upgrade duration is excluded.
Journal REST uses {items,has_more,limit,offset}; limit <=100, offset <=10000, inclusive opened_at date
filters require timezone. Time filters narrow deeper history. Newest-first order has UUID tie-breaking.

## Concurrency and performance

Claims use `FOR UPDATE SKIP LOCKED`; an expired UUID lease fences stale results. Unit/integration
tests cover disjoint claims for 50 rows and stale completion. This does **not** constitute the
required 50-monitor/30s multi-cycle load test. The separate live phase-2 smoke holds a monitor paused for over 30s, edits during HTTP,
restarts backend/worker, and asserts settings/group persistence without stale or fake failures:
`python scripts/phase2_smoke.py`. It touches only its own uniquely named resources.
Evidence: [phase-2 smoke](artifacts/phase2-smoke.json). There is no published throughput or monthly
history benchmark yet. Those remain mandatory before final submission.

Cadence is completion + interval (fixed delay); slow checks extend their own cycle. Missing
server time creates no observations. Charts with explicit gaps and coverage are not yet built.

## Security and known limitations

- HTTP(S) only; validate all resolved addresses, reject non-global IPs, connect to validated IP.
- Original Host/SNI retained. Redirect following and environment proxies disabled; TLS verified.
- Requests use Connection: close to prevent numeric-IP pool TLS reuse across virtual hosts.
  The shared client still bounds active connections; keep-alive optimization is deferred.
- 1 MiB raw body cap, compressed responses rejected, matching is UTF-8 with replacement.
- Exact simulator origin is a local testing exception, never a global private-network bypass.
- No authentication/rate limiting/production egress firewall yet. Local trusted usage only.
- Monitor/group list cap is 500; observation history cap 100; incidents are paginated. No month aggregates yet.
- Worker logs JSON; API currently uses ordinary Uvicorn access logs.
- Container tags and Python build backend are not fully digest/hash locked. Python application
  versions and npm lockfile are pinned; dependency updates require rerunning verification.
- Full security audit and sustained load remain pending. Incident and SMTP retry/restart/lease faults are tested.

## Next iteration / roadmap

1. Review the v0.4 maintenance/email checkpoint and private feature branch.
2. Add public projection/privacy controls and real public-page reconnect tests.
3. Add coverage-aware charts and 24h/7d/30d uptime aggregates.
4. Improve delivery operator tooling if needed; no real SMTP provider is required for this assignment.
5. Measure mixed 50-monitor load, month history, actual restarts and run independent review.
6. Complete requirements audit, owner-authored ten-sentence essay and approved GitHub submission.

## AI-assisted development and attribution

OpenAI Codex performed implementation and command-driven verification with owner direction.
System identifies the GPT-6 family; exact model identifier needs owner confirmation.
Codex suits this work because changes, tests and local commands can be reviewed together.
See [AI disclosure](docs/ai-development.md), [actual prompt](docs/prompts/001-master-prompt.md),
[decisions](docs/decisions.md), [chronological log](docs/development-log.md),
[progress](docs/progress.md), [first PR summary](docs/pr-summary.md).
These PRs were created on the owner's later request for the completed checkpoints, preserving
actual commit dates and branch dependencies. See the chronological log for creation evidence.

The project was written from an empty workspace, without a third-party application template.
Libraries: FastAPI, Pydantic, SQLAlchemy, Alembic, asyncpg, HTTPX/httpcore, Uvicorn, React,
TypeScript, Vite, Vitest, Testing Library, pytest, Ruff, Playwright and Prettier.
Infrastructure: PostgreSQL, nginx, Docker Compose and Mailpit official images.
HTTPX transport/HTTPCore extension documentation informed numeric IP and SNI handling;
see source links in the decision log. These dependencies retain their own licenses; no
third-party product UI or assets were copied. No project license has been chosen by the owner.
Migration 0004 used Alembic schema autogeneration followed by source/constraint review and migration tests.
SMTP uses Python stdlib smtplib/EmailMessage; Mailpit verification follows its
[official API documentation](https://mailpit.axllent.org/docs/api-v1/).
