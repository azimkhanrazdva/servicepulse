# Phase 5 implementation contract

Starts from audited phase4 HEAD 442496f, branch feat/public-status-analytics. Owner explicitly
accepted v0.4 and authorized phase5 only. No standalone detailed phase5 prompt is present in
docs/prompts at discovery; original master requirements and current owner request are the baseline.

## Public boundary

Keep the management API/UI local on 8000/8080. Add a separate FastAPI entrypoint and public
frontend entrypoint on 8081. Public ASGI has only allowlisted public GET/SSE routes, no admin router,
OpenAPI, docs, write endpoints or CORS permission. Public nginx cannot proxy management routes.
These are additional deployable boundaries inside the existing backend/frontend codebases.

PublicPage and Publication store page slug/title/enabled/version and explicit per-monitor selection,
public label, unrelated public UUID and optional aggregated-history permission (default false).
Pages start disabled, publications start empty. Publication changes use their own page version and
do not edit monitor config, incident state or scheduler leases. No group inclusion/implicit opt-in.

REST and dedicated SSE share one explicit safe projection: public title/label/ID, known state,
last observation time/freshness and generic maintenance indicator. Never publish internal monitor ID,
URL/private name/group/recipient/expected content/error/config/window names or outbox details.
History is available only with that publication's explicit extra permission and has only aggregated
counts/uptime/coverage/latency. No raw check results/incidents/private errors. Public responses no-store.
Every SSE tick reloads enabled page/membership and safe projection in a fresh read-only snapshot;
revocation removes a service on the next tick (2s). No replay of previous private/admin events.
Already received bytes cannot be recalled. Trusted-local management remains unauthenticated and
must never be exposed alongside the public entrypoint.

## Analytics

Uptime is successful observed checks / observed checks, not inferred continuous wall-clock health.
Return null/NO DATA at zero samples, not 100%. Separate observed coverage from uptime. PostgreSQL
does time bucketing/count/success/mean/min/max and interval-capped coverage; Python handles only
bounded result buckets (288 for 24h, 336 for 7d, 360 for 30d). Composite monitor/time index bounds scans.
No loading a month of raw ORM results into Python; recent-results API remains backward compatible.

New results capture interval_seconds; legacy rows remain nullable because historical cadence cannot
be reconstructed honestly. Coverage spans [checked_at, min(next observation, checked_at + captured
interval)], clipped to query bounds; missing periods beyond that remain unobserved. Legacy rows
still count as observations but contribute no fabricated time coverage. Include all configuration
versions and maintenance outcomes; label this policy. Bucket gaps render separately, never connected
as a healthy line or zero latency. Mean latency includes elapsed time of failed checks.

## Verification gates

Migration 0005 additive/default-private plus legacy preservation. DB aggregate tests cover no data,
all-fail, window boundaries, gaps, mixed versions/cadences/legacy rows and real PostgreSQL queries.
Privacy tests inspect complete REST/SSE payloads and route/method guessing at public ASGI/nginx.
Browser tests use real worker/simulator, admin publication, two public clients/reconnect/revocation,
analytics and gap rendering. Run all original backend/component/browser/smoke/fault tests. Phase6
sustained 50x30 test/final security audit are not started or claimed by this stage.

## Acceptance issue carried forward

ACC-EMAIL-01: Phase4 cancels unattempted DOWN on quick recovery even outside maintenance. The
original employer expects DOWN then recovery mail for a confirmed outage; this exception can miss
both messages when dispatcher is slow/offline. It is an acceptance risk, not a blanket PASS for that
stronger interpretation. Preserve current policy/tests during phase5; final acceptance audit must
resolve whether an independent notification-policy fix is required. No silent change here.
