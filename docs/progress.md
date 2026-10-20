# ServicePulse progress — v0.5 checkpoint

Read AGENTS.md, requirements.md, architecture.md, phase5-design.md and phase5-checkpoint.md before resuming.
Owner explicitly accepted audited v0.4 and requested Phase5; Phase6 is not started.

## Completed

- Phases 1–4: real API/frontend/PostgreSQL/worker, versioned monitors/groups, incidents, maintenance,
  transactional outbox/dispatcher, real SMTP/fault/restart/two-client evidence; see historical checkpoints.
- Phase5 additive 0005: default-private pages, explicit per-monitor public label/history consent,
  public UUIDs, cadence snapshots only for new observations; exact old outbox/window rows preserved.
- Public-only ASGI/nginx/build and GET/SSE projection; no management routes/docs/mutations/bundle.
- Separate safe public two-client/reconnect/revocation flow and stale REST/disconnect protection.
- PostgreSQL 24h/7d/30d observed uptime/coverage/latency with bounded buckets and honest NO_DATA/gaps.
- Native charts/accessibility table; rolling history advances without new observations.
- Functional publication editor with 409 drafts; dashboard uptime/current outage/active incident count.
- Final local checks: 121 backend, 26 component, seven browser tests; all original cases retained.
- Actual prior-stage smoke/restart/32s/proxy/Mailpit/DB/process-fault suites rerun and passed.
- Original notification policy unchanged; ACC-EMAIL-01 explicitly tracked for final employer acceptance.
- Real local backend c489815 and UI/integration 9c155c3 commits, privately pushed after local gates.

## In Progress

Phase5 completed and verified; waiting for owner review. Hosted run 39390308186 passed on exact
implementation 9c155c3335a4bf035c8a398b7b5f31a0940e16aa: backend, frontend and actual Compose/
Chromium browser jobs successful. Phase6 has not started. Final evidence handoff changes docs only.

## Blocked

No local Phase5 blocker. ACC-EMAIL-01 remains HIGH final-acceptance risk: queued unattempted DOWN
is cancelled on quick recovery even outside maintenance, potentially missing both employer-expected
emails during dispatcher delay/outage. Owner explicitly requested recording, not silently changing it.
Production public hosting/TLS/rate limits/shared DB role need later review; management stays local.
Exact AI model identifier and owner-authored ten-sentence essay still need owner confirmation/input.

## Next Tasks

1. Owner reviews verified v0.5: phase5-checkpoint.md, requirements.md, review.md and exact hosted CI.
2. Owner reviews the checkpoint before authorizing further work; no Phase6 performed here.
3. Later Phase6: sustained 50x30s mixed targets, larger-history/p95, final security/reliability audit.
4. Resolve ACC-EMAIL-01 in a separately explicit policy fix before claiming strict email compliance.
5. Later submission: full acceptance audit, owner essay, employer access and approved final delivery.
6. PR5 summary is prepared in pr-phase5.md. No new PR/merge/public visibility permission inferred.

## Verification Status

PASS local: 121 PostgreSQL tests, zero skips/failures; 0001/2/3/4 fixtures -> 0005 plus ORM check.
26 component tests; typecheck/lint/format/build; npm audit zero findings. Seven actual browser tests
passed in 18.5s, including public REST/SSE sentinels, route/method isolation, real worker DOWN/UP,
two public clients/reconnect, revoked history/page, mobile width and genuinely unobserved NO_DATA.
Raw reports: artifacts/backend-tests.xml, frontend-tests.json, browser-tests.json,
phase5-public-browser.json and consolidated phase5-checkpoint.json.
PASS hosted: run 39390308186 on 9c155c3, backend job63s (121 tests/20.49s), frontend34s (26 tests),
browser157s (seven tests/56.5s). Downloaded hosted browser report has 0 skipped/unexpected/flaky.
Actual structured evidence: artifacts/github-ci-phase5.json and github-browser-phase5.json.

Actual prior-phase regressions: smoke 0.609s, phase2 56.797s, phase3 57.578s, different-IP proxy
6.297s, phase4 fault 74.672s, all PASS. Crash still physical3/logical2: exactly-once SMTP not claimed.
Dense SQL fixture: 10000 rows / one query / 360 buckets / 0.055304s; not p95/unlimited-scale proof.
NOT VERIFIED: sustained 50x30s, larger-history/p95, final full security audit, external TLS/mailbox delivery.

## Current Branch

feat/public-status-analytics, based on audited phase4 442496f980b7e9ef14179b1895bdcbf517f5152c.
Private origin: https://github.com/azimkhanrazdva/servicepulse.
Existing PRs: #1 phase2->main, #2 phase3->phase2, #3 phase4->phase3; none merged or retargeted.
No Phase5 remote PR created. Never force-push or squash/rebase the shared dependency chain.

## Latest Commit

Implementation 9c155c3335a4bf035c8a398b7b5f31a0940e16aa, 2026-10-20T08:00:13+05:00,
feat(ui): ship public status analytics and privacy regression.
Backend c489815, 2026-10-20T07:43:50+05:00. A docs-only hosted-evidence handoff follows;
git log -1 resolves HEAD without a self-referential hash in this file.

## Important Context

No automatic publication or demo publication. Owner chooses each public label and history permission;
public root deliberately returns404, use /status/{slug} on localhost:8081. E2E removes its own pages.
Public history permission includes aggregate observations before publication, all configs/maintenance;
legacy cadence stays unknown. Missing observations never become DOWN or fabricated 100% uptime.
API/UI management 8000/8080 and Mailpit8025 are trusted-local, not public; expose only public ingress.
Read-only DB transactions share the existing role; production privilege/ingress hardening not claimed.
Public authorization is per request/tick; previously received bytes cannot be recalled.
Notifications, leases/config fencing and administrative incident semantics remain phase4 contracts.
Historical evidence: phase2-checkpoint.md, phase3-checkpoint.md, phase4-checkpoint.md, phase4-audit.md.
No fake timestamps/tests/metrics/commits, no phase6 work, no automatic PR/merge/publication.
