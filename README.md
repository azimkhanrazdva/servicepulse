# ServicePulse

**v1.0 candidate — technically verified local runtime, ready for owner approval.**
Built for Mad Devs Junior Agentic Developer assignment #3. This is a client/server website
availability monitor with real HTTP observations, incidents, local SMTP, isolated public status
pages and observed uptime analytics. It is not submitted or a certified production deployment.
Exact model confirmation, the owner's personal essay and employer repository access remain pending.

See the [final checkpoint](docs/phase7-checkpoint.md), [current per-ID acceptance](docs/phase7-final-acceptance.md),
[demo script](docs/demo-script.md), [submission guide](docs/submission-guide.md),
[security scope](docs/phase7-security-review.md) and [performance evidence](docs/phase7-performance.md).

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
- Monochrome responsive React dashboard, real HTTP code/latency/timestamps and recent observation history.
- SSE snapshots and automatic browser reconnect; full resynchronization on the next snapshot.
- Alembic migration, isolated PostgreSQL integration tests, HTTP simulator and Mailpit container.
- URL/DNS destination policy, pinned numeric connections, no redirects/proxies, bounded response/time.

Public pages are disabled/empty by default. Publish each service explicitly with a separate public label;
aggregated history requires a second permission. The public image has no management bundle or admin routes.
Actual SMTP/Mailpit tests and failure evidence are in [phase 4 checkpoint](docs/phase4-checkpoint.md).
The technical runtime checkpoint is verified within its documented limits. Submission remains an owner action. See [acceptance matrix](docs/requirements.md).

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

Docker Engine/Desktop with Linux containers and Docker Compose2.24.4+; free localhost ports
8080 (management UI), 8000 (management API), 8081 (public-only ingress), 8025 (Mailpit).
Initial image/dependency download needs internet. All host ports bind loopback by default.
Windows PowerShell, macOS and Linux are supported by Compose; development was verified on
Windows with Docker Desktop. Python 3.11+ is only required for host smoke/seed scripts.

PowerShell preparation (once):

```powershell
if (-not (Test-Path .env)) { Copy-Item .env.example .env }
```

macOS/Linux preparation: `[ -f .env ] || cp .env.example .env`. Preserve an existing configuration. Then the same startup command everywhere:

```sh
docker compose up -d --build --wait
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
The 0004 fixture additionally preserves actual maintenance/outbox/delivery rows through 0005,
with no automatic publications and no inferred cadence for legacy observations.
The0005 fixture preserves public pages/publications and captured cadence through0006;
the earlier outbox fixture checks its existing delivery rows across the same upgrade;
unknown legacy notification eligibility is not guessed or replayed.

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
Phase7 captured [desktop](output/playwright/phase7-monochrome/1440-overview.png) and
[mobile](output/playwright/phase7-monochrome/390-overview.png) are real screenshots with test fixtures.
Current evidence:150 backend,32 components,12 Chromium cases,0 unexpected/flaky/skipped;
12 axe scans with0 violations (incomplete checks retained, not WCAG certification).
Reports: artifacts/phase7-backend-tests.xml, phase7-frontend-tests.json, phase7-browser-tests.json.
Historical checkpoint files retain their original results rather than being rewritten to current counts.

Phase4 live fault suite: `python scripts/phase4_fault_smoke.py`. It creates a separate Compose project,
ports 18000/18025 and its own DB volume; tests SMTP outage, restart, DB outage and acceptance-before-ack
crash, then stops only that isolated project and retains its volume. No database volumes are removed. Leave these ports free. Evidence is in
artifacts/phase4-fault.json and phase4-fault.log. Browser integration also checks actual Mailpit receipts.
On restricted Windows execution, local socket access and launching Chromium may require
host permission. A sandbox denial is not proof of an application failure or passing test.

GitHub Actions runs Python lint/format/PostgreSQL tests, frontend format/tests/types/build/audit,
and real Docker Compose/Chromium E2E. Exact code-checkpoint42e4001 passed all3jobs in [Actions39463440225](https://github.com/azimkhanrazdva/servicepulse/actions/runs/39463440225),
with150backend/32component/12browser tests and downloaded12axe0violations. Snapshot: artifacts/phase7-ci.json.
The final documentation-head SHA gets a separate live Actions check reported at handoff; never substitute
a previous green run for a changed commit.
The genuine [development log](docs/development-log.md) records exact run URLs and failures.

Private repository: [azimkhanrazdva/servicepulse](https://github.com/azimkhanrazdva/servicepulse).
Current candidate branch is feat/final-acceptance-release, stacked on feat/reliability-audit-redesign.
main still records the original v0.1 baseline. Existing real open PRs:
[Phase2 #1](https://github.com/azimkhanrazdva/servicepulse/pull/1),
[Phase3 #2](https://github.com/azimkhanrazdva/servicepulse/pull/2),
[Phase4 #3](https://github.com/azimkhanrazdva/servicepulse/pull/3).
No merge or Phase5/6/7 PR creation was authorized. Prepared summaries/dependency/merge commands are
in [GitHub workflow](docs/github-workflow.md). A1.0.0 package label is not a GitHub Release/tag.

### Additional reproducible acceptance commands

Run experiments sequentially, with their named ports free. Python3.11+, Node24, npm ci and
installed Chromium are required for the host harnesses. Test recipients are local Mailpit only.

```powershell
python scripts/phase7_clean_checkout.py --ref feat/final-acceptance-release
# New isolated project/DB; ports28000/28080/28081/28025; volumes retained.
$env:FAULT_EVIDENCE_PREFIX = 'phase7-smtp-faults'
python scripts/phase4_fault_smoke.py
Remove-Item Env:FAULT_EVIDENCE_PREFIX
python scripts/phase6_email_smoke.py
python scripts/phase7_acceptance_audit.py
# Expensive, optional repeat of existing measured experiments:
python scripts/phase6_load.py
python scripts/phase6_fault_load.py
python scripts/phase6_cold_history.py
```

The immutable clean-runtime test uses a committed clone and new schema0006 database, verifies HTTP
persistence/settings/groups after restarts and runs the complete browser journey. It shares the
host/Docker layer cache and uses isolated port overrides, not a fresh operating system.
The acceptance audit rechecks retained raw data and the authored matrix; it does not rerun load
or promote documentation existence to a passing product test. Commands may overwrite fixed report
paths; copy new reports with their actual stage prefix before restoring historical tracked evidence.

## Public status and observed analytics

In the dashboard's **Public status pages** section, create a page, enter a title and slug,
select each permitted monitor and supply its public label. Enable the page explicitly.
Select **Publish aggregated history** separately if the public may see that service's history.
Open its link, for example `http://localhost:8081/status/customer-status`. The root `/` on
8081 deliberately returns 404; there is no directory of private or disabled pages.
New installations/migrations publish nothing automatically. Test pages are removed after E2E.

Only public ingress 8081 is suitable for a future public reverse proxy; never expose management
8080/8000 or Mailpit. Management has no login. Host TLS/rate limits/operations remain later work.
Public REST and dedicated SSE are separate from management:

- `GET /api/public/pages/{slug}` — safe current projection.
- `GET /api/public/pages/{slug}/events` — public-only snapshots every two seconds.
- `GET /api/public/pages/{slug}/services/{public_id}/analytics?period=24h|7d|30d` — explicitly permitted aggregates.

Unknown/disabled pages and denied history return generic 404. A public ID is unrelated to the
internal monitor UUID. No URL, private name, group/recipient/config/raw errors or outbox data is
exposed. Revocation is rechecked on every request/tick; previously received bytes cannot be recalled.
Public disconnect clears displayed data; reconnect obtains current permissions and a full snapshot.

Private details include `GET /api/monitors/{id}/analytics?period=24h|7d|30d` and real charts.
Availability is successful observed checks / observed checks, including maintenance/config versions.
Zero observations means **NO DATA**, not 100%. Coverage is a separate estimate using interval-capped
observation spans. Legacy cadence remains unknown; it is not backfilled. Missing buckets stay gaps,
never failed checks or zero latency. SQL returns at most 288/336/360 buckets respectively; raw recent
history still returns the latest 100 checks for compatibility. See [design](docs/phase5-design.md).

Management publication API: GET/POST `/api/status-pages`; PUT/DELETE `/api/status-pages/{id}`
with the captured `config_version`. Publication edits never reset monitoring state or incidents.

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

New incidents use migration0006's persisted notification obligation. Confirmed outages eligible outside maintenance retain ordered DOWN then RECOVERY even if recovery precedes dispatcher processing. Incidents entirely inside applicable maintenance are suppressed; an ended window while still DOWN earns the alert obligation. All revoked routes cancel terminally. PAUSED/CONFIG_CHANGED closes administratively without recovery; pending DOWN cancels on preflight. Legacy unknown eligibility retains the prior policy and is not reconstructed or mass-mailed. SMTP acceptance can remain ambiguous after a crash; physical duplicates are possible. See [current policy](docs/phase6-notification-policy.md).

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

Claims use `FOR UPDATE SKIP LOCKED`, UUID fencing and expiry checks. Real steady50×30s experiments and a separate50-monitor fault matrix verify logged non-overlap and slow/fast independence. History benchmarks include synthetic datasets up to1m fleet rows and100k on one service; distribution and cold/warm limits are explicit in [performance evidence](docs/phase6-performance.md). New scoped JIT policy uses one local setting plus one bounded aggregate SELECT, with at most360 monthly buckets. Measured warm p95 is867ms but an outlier is1.180s; no universal subsecond claim.

Cadence is completion plus interval (fixed delay). Missing server time creates no observations; charts distinguish gaps/coverage from sample uptime. Local regression commands/evidence: [v0.6 checkpoint](docs/phase6-final-checkpoint.md).

## Known limitations and security

- HTTP(S) only; validate all resolved addresses, reject non-global IPs, connect to validated IP.
- Original Host/SNI retained. Redirect following and environment proxies disabled; TLS verified.
- Requests use Connection: close to prevent numeric-IP pool TLS reuse across virtual hosts.
  The shared client still bounds active connections; keep-alive optimization is deferred.
- 1 MiB raw body cap, compressed responses rejected, matching is UTF-8 with replacement.
- Exact simulator origin is a local testing exception, never a global private-network bypass.
- No authentication/rate limiting/production egress firewall yet. Local trusted usage only.
- Monitor/group list cap is 500; recent raw history cap 100; incidents are paginated. Analytics uses bounded SQL buckets.
- Public requests use a separate read-only ASGI application and read-only transactions; the database role
  is shared, not a dedicated least-privilege account. Public hosting still needs ingress limits/TLS/operations review.
- Worker logs JSON; API currently uses ordinary Uvicorn access logs.
- Container tags and Python build backend are not fully digest/hash locked. Python application
  versions and npm lockfile are pinned; dependency updates require rerunning verification.
- Scoped security review, sustained/fault load and incident/SMTP regressions are completed for the documented local boundary; this is not production certification.

## Next iteration / roadmap

Before26October2026: owner reviews this candidate, confirms the exact model, writes/approves the
ten-sentence essay, authorizes any desired PR/merge actions and grants employer private access.
No employer email is sent by the agent. See [submission guide](docs/submission-guide.md).
Later work: authenticated management, dedicated public DB role, ingress/egress budgets, controlled
production SMTP/TLS, management pagination beyond500, full state-change timeline, structured API
logs and manual screen-reader/WCAG review. [Roadmap](docs/roadmap.md) separates these from delivered work.

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
TypeScript, Vite, Vitest, Testing Library, pytest, Ruff, Playwright, axe-core (test-only) and Prettier.
Infrastructure: PostgreSQL, nginx, Docker Compose and Mailpit official images.
HTTPX transport/HTTPCore extension documentation informed numeric IP and SNI handling;
see source links in the decision log. These dependencies retain their own licenses; no
third-party product UI or assets were copied. No project license has been chosen by the owner.
Migration 0004 used Alembic schema autogeneration followed by source/constraint review and migration tests.
SMTP uses Python stdlib smtplib/EmailMessage; Mailpit verification follows its
[official API documentation](https://mailpit.axllent.org/docs/api-v1/).
