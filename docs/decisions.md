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
