# Prepared Phase5 PR summary (no remote PR created)

Title: feat: isolate public status and add observed availability analytics

Base: feat/maintenance-email-outbox (audited 442496f), head feat/public-status-analytics.
This would depend on actual PR #3, not main. Creating/merging another PR requires owner authorization.

The private dashboard previously lacked public projection and aggregate history. Add explicit disabled/
empty publication controls with unrelated public IDs/labels and extra history consent, isolated public
ASGI/nginx/build, safe public GET/SSE with fresh authorization, bounded PostgreSQL sample uptime/
coverage/latency buckets, native charts/gaps and real dashboard incident/uptime summaries.

Additive 0005 preserves 0004 maintenance/outbox/history and publishes nothing automatically. New
observations capture cadence; old cadence remains NULL. Phase4 notification policy remains unchanged;
ACC-EMAIL-01 is explicitly carried as HIGH final acceptance risk rather than silently redefined.

Validation: 121 PostgreSQL tests/migration fixtures, 26 component tests, seven real browser scenarios,
original phase1–4 live restart/slow/proxy/SMTP/DB/crash regression, lint/types/format/build/audit.
Dense 10000-row fixture returns 360 buckets with one SQL query; this is not sustained fleet evidence.
See phase5-checkpoint.md, actual reports and development-log.md for current hosted CI outcome.

Boundaries: local trusted management, shared DB role/read-only transactions, no production TLS/rate
limits claim; in-flight bytes cannot be recalled. Full 50x30/larger-history/final security audit later.
No human/independent approval, merge or public repository visibility change claimed.
