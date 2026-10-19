# ServicePulse

A website availability monitoring platform built for Mad Devs' Junior Agentic Developer
take-home assignment #3. **Version 0.2 adds verified monitor/group management; incidents, notifications and public status remain pending.**

Create a monitor, let an independent worker request a real HTTP target, persist observations
in PostgreSQL and see the dashboard update through SSE. No fabricated metrics or HTTP results.

## Current features

- Create/edit/delete/pause/resume/run-now through React and API; configurable interval, timeout, status, body match and confirmation threshold.
- Versioned edits with explicit conflict recovery; active HTTP leases survive changes and stale results are discarded.
- Group CRUD, many-to-many membership, aggregate status and validated per-group email recipients (storage only).
- Separate asynchronous worker with bounded concurrency, durable scheduling, fenced database leases.
- UNKNOWN → UP/DOWN state with two consecutive failures by default; manual run queue.
- Dark responsive React dashboard, real HTTP code/latency/timestamps and recent observation history.
- SSE snapshots and automatic browser reconnect; full resynchronization on the next snapshot.
- Alembic migration, isolated PostgreSQL integration tests, HTTP simulator and Mailpit container.
- URL/DNS destination policy, pinned numeric connections, no redirects/proxies, bounded response/time.

**Not implemented:** persisted incidents, email/outbox,
maintenance, public status page, uptime aggregates, response charts, monthly history endpoint.
Mailpit running does not mean email notifications work. See [acceptance matrix](docs/requirements.md).

## Architecture and stack

React 19 + TypeScript + Vite → nginx same-origin proxy → FastAPI → PostgreSQL 17.
A separate Python 3.12 worker claims work in PostgreSQL and uses asynchronous HTTPX.
SQLAlchemy 2 and Alembic manage persistence. No Redis, Celery or distributed broker.
SSE sends full snapshots every two seconds; small-scale database polling is intentional.

See [architecture](docs/architecture.md) and [decisions](docs/decisions.md) for models,
state policy, intended incident/outbox design, alternatives and limitations.

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

`CONCURRENCY` and `MAX_BODY_BYTES` are application environment variables; add them explicitly
under the shared backend environment in Compose to override defaults. `.env` is ignored.
There are no real keys or SMTP credentials in the repository. Current mail service is only a catcher.

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
This changes displayed state only; incident records and email are subsequent work.

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
| GET / PUT / DELETE | /api/groups/{uuid} | Read / versioned replacement / versioned deletion |
| GET | /api/events | Monitor array + named groups event from one DB snapshot every 2 seconds |

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
asserts their settings, IDs, state and history survive upgrade to 0002 before running the suite. This never resets the application's `db` volume.

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
On restricted Windows execution, local socket access and launching Chromium may require
host permission. A sandbox denial is not proof of an application failure or passing test.

GitHub Actions specifies Python lint/format/PostgreSQL tests and frontend format/tests/types/build.
Hosted CI is **NOT VERIFIED** until a repository is published and Actions actually runs.
Private repository: https://github.com/azimkhanrazdva/servicepulse. main records v0.1;
feat/monitor-management-groups carries v0.2 after its verified stage push. No remote PR or merge is claimed.
See [GitHub workflow](docs/github-workflow.md) for the authentic baseline and publication policy.

## Management semantics

Editing any monitor field resets current metrics/streak and UNKNOWN state, retaining historical
observations with their config_version; paused monitors stay PAUSED. Old HTTP work keeps its lease
until completion/expiry and cannot commit stale observations. Resume sets UNKNOWN and schedules now.
Two same-version edits cannot silently overwrite each other: the loser gets 409, keeps its draft,
and explicitly discards/reloads before retrying. Name-only edits follow the same reset policy.

Groups ignore PAUSED members, then choose DOWN over UNKNOWN over UP. All paused gives PAUSED;
empty gives UNKNOWN. Membership and recipient replacement is atomic; deleting a group keeps monitors.
Recipients are syntactically validated/deduplicated; **no email is sent in v0.2**.

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
- List/SSE cap is 500; history cap 100; no pagination or full month query yet.
- Worker logs JSON; API currently uses ordinary Uvicorn access logs.
- Container tags and Python build backend are not fully digest/hash locked. Python application
  versions and npm lockfile are pinned; dependency updates require rerunning verification.
- Full security audit, process-restart fault tests and SMTP retry tests remain pending.

## Next iteration / roadmap

1. Review the v0.2 management checkpoint and private feature branch.
2. Persist incident lifecycle and transactional outbox; maintenance suppression/reconciliation.
3. Deliver group email through Mailpit with logical deduplication and retries.
4. Finish charts, uptime with coverage, incident UI and public projection/privacy tests.
5. Measure mixed 50-monitor load, month history, actual restarts and run independent review.
6. Complete requirements audit, owner-authored ten-sentence essay and approved GitHub submission.

## AI-assisted development and attribution

OpenAI Codex performed implementation and command-driven verification with owner direction.
System identifies the GPT-6 family; exact model identifier needs owner confirmation.
Codex suits this work because changes, tests and local commands can be reviewed together.
See [AI disclosure](docs/ai-development.md), [actual prompt](docs/prompts/001-master-prompt.md),
[decisions](docs/decisions.md), [chronological log](docs/development-log.md),
[progress](docs/progress.md), [first PR summary](docs/pr-summary.md).
No remote PR exists at this checkpoint; private GitHub upload is authorized after verified stages.

The project was written from an empty workspace, without a third-party application template.
Libraries: FastAPI, Pydantic, SQLAlchemy, Alembic, asyncpg, HTTPX/httpcore, Uvicorn, React,
TypeScript, Vite, Vitest, Testing Library, pytest, Ruff, Playwright and Prettier.
Infrastructure: PostgreSQL, nginx, Docker Compose and Mailpit official images.
HTTPX transport/HTTPCore extension documentation informed numeric IP and SNI handling;
see source links in the decision log. These dependencies retain their own licenses; no
third-party product UI or assets were copied. No project license has been chosen by the owner.
