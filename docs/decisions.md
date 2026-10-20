# Decision log

## ADR-001 — owner stack and runtime
Context: independent backend/frontend, relational persistence and asynchronous I/O required.
Decision: FastAPI, Pydantic, SQLAlchemy 2, Alembic, PostgreSQL, React/TypeScript/Vite.
Python 3.12 in containers; local Python 3.11 remains supported for tests.
Alternatives: Go or Node API, Vue UI. Trade-offs: async database sessions require care.
Consequences: retain the owner's preferred stack and typed boundaries; no Redis/Celery/Kafka.

## ADR-002 — PostgreSQL scheduler
Context: no overlapping runs, crash recovery, low fleet size and separate worker.
Decision: small asyncio loop, row claims with SKIP LOCKED, expiring fenced leases.
Alternatives: APScheduler, Celery. Trade-offs: own a small scheduling implementation and
dedicated concurrency tests; fixed delay cadence does not guarantee exact wall-clock intervals.
Consequences: one operational source of truth, bounded tasks, no extra queue service.

## ADR-003 — SSE snapshots
Context: two clients and reconnect synchronization, server-to-browser updates only.
Decision: complete snapshots every two seconds through SSE, same-origin nginx proxy.
Alternatives: WebSocket, browser polling, DB NOTIFY. Trade-offs: small periodic database read,
not instant event delivery. Consequences: API replicas need no shared in-memory event bus.

## ADR-004 — confirmation and outbox (target)
Context: transient errors and retrying SMTP must not duplicate logical alerts.
Decision: two consecutive failures by default, unique incident/event keys, transactional outbox.
Alternatives: send email inside check task. Trade-offs: SMTP cannot guarantee physical exactly-once.
Consequences: incidents/outbox must ship together with maintenance reconciliation and race tests;
initial state logic alone does not satisfy notification requirements.

## ADR-005 — safe destination pinning
Context: user-controlled URLs create SSRF and DNS-rebinding risks.
Decision: validate all DNS answers and connect to chosen numeric IP with original Host/SNI,
disable redirects and proxies, cap streamed bytes/time. Narrow opt-in simulator origin.
Alternatives: validate DNS then use hostname (rebinding race), hostname allowlist only.
Trade-offs: no redirects or compressed responses initially; single chosen address may fail
even when another address is reachable. Consequences: test construction and deny private DNS;
add live TLS test and network egress defense before public deployment.
Sources: [HTTPX transports](https://www.python-httpx.org/advanced/transports/),
[HTTPCore SNI extension](https://www.encode.io/httpcore/extensions/).

## ADR-006 — optimistic editing with retained leases
Context: two clients may edit the same monitor while HTTP work is running.
Decision: captured integer config_version plus row lock; 409 preserves the losing draft.
Keep active lease through edit/pause/resume; discard stale version results before/after I/O.
Every edit resets current metrics/state, retaining versioned history. Resume schedules UNKNOWN.
Alternatives: last-write-wins loses edits; clearing leases can start overlapping requests;
holding a DB transaction over the network occupies connections and locks excessively.
Trade-offs: a changed monitor may wait for the old request/lease; rename also resets state.
Consequences: deterministic conflict UX, simple durable recovery; incident interactions belong to phase 3.

## ADR-007 — normalized groups and independent versions
Context: membership, per-group recipients and aggregate state must remain consistent.
Decision: join table and recipient table with FK cascades; group row version guards full replacement.
Lock group then selected monitors in UUID order; monitor settings and group edits use separate versions.
Group state: ignore paused members, then DOWN > UNKNOWN > UP; all paused PAUSED, empty UNKNOWN.
Alternatives: embedding membership/recipients in JSON, one global settings version.
Trade-offs: extra small queries; not an unbounded-fleet aggregation implementation.
Consequences: no silent lost same-group edits; deleting a group retains monitors; email sending stays deferred.

## ADR-008 — authentic GitHub baseline
Context: first slice already consisted of a root code commit plus docs; no main/origin existed.
Decision: owner authorized stage uploads and chose private visibility. Create main at existing
bd43629 and publish main plus first-slice branch unchanged. Phase 2 branches from that same head.
Alternatives: synthetic empty root to manufacture a first full-code PR, rewriting the initial commits.
Trade-offs: no meaningful full first-slice PR (branches have identical trees); first slice is reviewed
through actual commits, subsequent stage gets a meaningful main...feature diff.
Consequences: authentic original history, private repo, no automatic PR/merge or force-push.
Repository: https://github.com/azimkhanrazdva/servicepulse. Owner controls employer access.

## ADR-009 — confirmed incidents and administrative closure (phase 3)
Context: DOWN records must survive restart, retries and concurrent mutations; pause/edit are not recovery.
Decision: incident UUID with separate closed_at and recovered_at; partial unique open-monitor key on
closed_at IS NULL. Worker updates incident, state and observation in the existing row-locked transaction.
Edits (including rename) close CONFIG_CHANGED; pause closes PAUSED; only success closes RECOVERED.
Alternatives: overload recovered_at for all closures; application-only uniqueness; event infrastructure now.
Trade-offs: one extra timestamp; rename still resets an outage per v0.2's conservative configuration policy;
deletion removes history; physical email delivery/idempotency awaits phase 4.
Consequences: unambiguous later outbox events and stable incident identity. This phase separation, explicitly
requested by the owner, supersedes ADR-004's original suggestion to ship incidents/outbox together.

## ADR-010 — legacy DOWN and bounded journal synchronization
Context: v0.2 DOWN observations cannot prove an earlier incident confirmation timestamp.
Decision: additive migration leaves existing data unchanged and creates no incident backfill. A fresh failed
observation opens the first tracked incident; a fresh success with no incident creates no recovery event.
Reuse SSE invalidation with bounded REST journal pages and database joined reads; no new dependency.
Alternatives: infer historical incidents from incomplete samples; replace SSE; send all journal rows forever.
Trade-offs: pre-upgrade outage duration remains unknown; one extra REST request/client/two seconds;
offset cap 10000 (time filters narrow deeper history), page boundaries can move during concurrent inserts.
Consequences: honest provenance and reconnect synchronization, including changes to older visible pages;
future scale may justify keyset pagination and revision-only events, after measurement.

## ADR-011 — event, route and address delivery outbox
Context: one monitor can belong to multiple groups, with shared addresses and different maintenance.
Decision: unique incident/type event; frozen group/email routes at confirmation; unique event/email
delivery. Case-normalize delivery addresses. Preserve route group UUID historically without a group FK,
and require live membership/recipients at authorization. New recipients apply only to future incidents.
Alternatives: one outbox row/group (duplicates common addresses); JSON-only mutable payload; a broker.
Trade-offs: three small tables, extra eligibility joins, case-sensitive local parts intentionally treated
as one operational address; group UUID is historical, avoiding group->monitor/monitor->group FK inversion.
Consequences: one logical delivery/address across routes, group-specific maintenance and safe recipient
revocation, no external queue or new runtime dependency. DB constraints enforce identity, not in-memory sets alone.

## ADR-012 — SMTP authorization, ordering and finite retries
Context: SMTP cannot commit atomically with PostgreSQL, nor recall a command already in flight.
Decision: final DB policy preflight plus persisted send_started_at, then SMTP outside any DB transaction.
Cancelled unattempted DOWN produces no recovery. A possibly accepted attempt is retried before recovery;
known rejection clears authorization. RECOVERY requires the address's known DOWN acceptance and can wait
through maintenance. Admin closure never creates recovery. Persist 5..300s backoff, at most eight attempts.
Alternatives: hold DB transaction across SMTP; assume exactly-once delivery; send recovery before pending DOWN.
Trade-offs: post-authorization maintenance/setting changes cannot recall in-flight SMTP; ambiguous crash
can cause physical duplicates/stale DOWN. Exhaustion needs investigation. Bounded threads/socket timeouts
and lease margins do not guarantee non-overlap under arbitrary process suspension.
Consequences: explicit, tested boundary and stable Message-ID; real acceptance-crash experiment produced
3 physical messages for 2 logical deliveries, in correct event order. No eventual mailbox delivery promise.

## ADR-013 — no upgrade mass mailing; independent reconciliation
Context: v0.3 may contain historical/open incidents with no recipient intent at their confirmation.
Decision: 0004 adds notifications_enabled=false to existing incidents; only newly confirmed incidents
explicitly enable notifications. Persist pending events/routes even under maintenance; poll independently
of HTTP results to release/cancel deliveries. UTC windows use inclusive start/exclusive end, overlaps per route.
Alternatives: backfill old DOWN emails; invent CheckResult to trigger window-end logic; global group suppression.
Trade-offs: existing incidents do not start mailing after upgrade; SMTP batch duration adds to the two-second
poll cadence. All old results/settings/timestamps remain unchanged. No catch-up historical email is inferred.
Consequences: honest migration and deterministic late notification without duplicate incidents or fake observations.
# ADR-014 — explicit public boundary and publication consent (phase5)

Context: management has no login and must remain trusted-local, while the status page must be public/read-only.
Decision: separate public FastAPI entrypoint and nginx/frontend build, only public GET/SSE; no admin
router/OpenAPI or management bundle in the public image. Explicit PublicPage/Publication records,
disabled/empty defaults, unrelated public IDs, owner-written labels and extra opt-in for aggregates.
All public DB snapshots use read-only transactions and safe projection, refreshed on every SSE tick.
Alternatives: mount public routes beside admin; add full authentication. Trade-offs: two extra small
Compose processes reuse existing code/runtime; same DB role with read-only transactions is not a
separate least-privilege database identity. Consequences: expose only public ingress, never management
ports. In-flight authorized bytes cannot be recalled; next-tick revocation and no-store prevent replay.

# ADR-015 — observed uptime, bounded SQL buckets and explicit gaps (phase5)

Context: month history cannot load all observations into Python or pretend server downtime is failure.
Decision: indexed PostgreSQL aggregates with 288/336/360 buckets for rolling 24h/7d/30d; uptime is
observed successful checks / observed checks, null at zero samples. Report interval-capped observed
coverage separately; capture new observation cadence without backfilling unknown legacy cadence.
Native SVG bucket bars and accessible data table show real mean elapsed latency with empty buckets.
Alternatives: time-weighted SLA interpolation, ORM aggregation, an extra chart dependency.
Trade-offs: bounded response but indexed scan still grows with observations; phase6 must measure
larger datasets/fleet performance. Sample uptime is not a continuous-time SLA, coverage is an estimate.
Consequences: history includes all config versions and maintenance outcomes; gaps never become DOWN,
zero latency or invented 100% availability. No new runtime dependency needed for the charts.
