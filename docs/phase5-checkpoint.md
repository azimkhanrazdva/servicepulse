# ServicePulse v0.5 — public status and observed analytics

Phase5 local gate verified; private stage upload/hosted CI recorded in the chronological log after execution.
Branch feat/public-status-analytics starts at audited v0.4 442496f. First backend increment:
c489815, feat(api): isolate public status and aggregate observed availability, 2026-10-20T07:43:50+05:00.
No rewrite/merge of previous stages, no automatic public repository/PR creation. Phase6 not started.

## Delivered

- Additive Alembic 0005: disabled PublicPage, explicit Publication, separate public UUID/label,
  optional history permission; nullable captured cadence for new observations. No implicit publication
  or invented historical cadence. Actual 0004 outbox/window/sent-delivery fixtures preserved through 0005.
- Separate public-only FastAPI entrypoint and nginx/image (8081); no management routes/docs/writes
  or management JS bundle. Management 8000/8080 remains trusted-local and unauthenticated.
- Explicit GET/SSE projection shared by two public clients: known state, freshness, observation time,
  safe labels and generic maintenance badge. No private names/URLs/IDs/recipients/config/errors/outbox.
  No-store; fresh authorization on each request/tick, removal on revocation; in-flight bytes cannot be recalled.
- Functional private page editor with disabled/empty defaults, monitor consent, public labels,
  history opt-in, version conflicts/draft preservation and actual links. No automatic group publication.
- PostgreSQL 24h/7d/30d aggregates with bounded buckets and sample-based uptime; no raw-month ORM load.
  Zero observations returns null/NO_DATA. Separate interval-capped coverage; legacy unknown cadence stays unknown.
- Native SVG response-time bars, genuine empty-bucket gaps and accessible aggregate table. Metrics refresh on
  new observations, reconnect and every minute even when the worker is stopped. No bridging missing observations.
- Dashboard 24h observed uptime (30s aggregate refresh), live exact active-incident count and current-outage
  duration from persisted incident start. Cheap live metadata is separate from heavy sample aggregation.

## Verification

- Final local backend: **121 PASS**, no skips/failures; 0001/2/3/4 legacy migration fixtures and metadata PASS.
  Run time 29.24s (JUnit suite 29.235s). Public route/method guessing, exact payload keys, sentinel leakage,
  read-only transaction enforcement, revocation, generic failures, parallel edits and cascades included.
- Final local component: **26 PASS**; types, ESLint, Prettier and production build PASS; npm audit zero findings.
  Added NO_DATA-vs-zero, periodic window advancement, aborted/failed history, public reconnect/revocation/
  late REST race, publication defaults/409 drafts and ticking outage duration checks.
- Full real browser gate: seven tests (all original five retained), including public admin opt-in,
  REST/SSE privacy, two public clients, DOWN/UP/reconnect, permission removal/disable, mobile width,
  real PostgreSQL charts and genuinely unobserved paused service showing NO DATA for all periods.
  Current measured duration is in artifacts/browser-tests.json, not fabricated from an estimate.
- Dense SQL fixture: **10000 rows → one query → 360 buckets**, 90% observed success, partial coverage.
  Latest measured aggregate **0.055304s**, from backend JUnit suite properties. Not p95, not universal latency.
  Environment: Docker Linux/x86_64, 16 reported CPUs, 8170147840 bytes memory; Python 3.12.15,
  PostgreSQL 17.11 Alpine; host Node v24.15.0 on Windows. Dataset generated only in disposable test DB.
- Earlier-stage live regressions actually rerun: smoke **0.609s**, phase2 pause/edit/restart **56.797s**,
  phase3 incident/restart/32s target **57.578s**, different-IP nginx recovery **6.297s**,
  isolated phase4 SMTP/DB/process faults **74.672s**, all PASS. Physical acceptance crash remains
  3 messages/2 logical deliveries; existing notification policy unchanged.

Commands: docker compose up -d --build --wait; docker compose --profile test run --rm --build tests;
ruff check/format --check backend; frontend npm test/typecheck/lint/format:check/build/audit/test:e2e;
python scripts/smoke.py, phase2_smoke.py, phase3_smoke.py, proxy_recreate_smoke.py, phase4_fault_smoke.py.
Actual errors/fixes and command timestamps are in development-log.md. No tests removed/weakened.

## Boundaries and final acceptance

Read [phase5 design](phase5-design.md), [review](review.md), [matrix](requirements.md) and machine
report artifacts/phase5-checkpoint.json. Public history opt-in publishes aggregates from before
publication too, including all configuration versions/maintenance; no raw errors or private config.
Read-only transactions use the shared DB role, not separate database privileges. TLS/rate limits/
production exposure and sustained 50x30 fleet/larger-history measurement remain later gates.

**ACC-EMAIL-01 remains OPEN/HIGH for final employer acceptance:** an unattempted DOWN may be cancelled
after quick recovery outside maintenance, so dispatcher delay can miss both emails. Owner explicitly
asked to preserve policy during this phase. Do not turn this into an unconditional notification PASS.
No full-assignment completion, Phase6 load test or independent human approval is claimed.

To inspect: run Compose, open localhost:8080; create a status page under Public status pages,
choose permitted services/public labels/history and enable it. Open localhost:8081/status/{slug}.
Root public ingress deliberately 404s and migrations publish nothing. E2E leaves no test publications.
