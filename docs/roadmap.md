# Roadmap — remaining scope, not future history

System date2026-10-20; owner deadline2026-10-26. Technical Phase7 candidate is at owner review; no autonomous work after this session is promised. See progress.md and the genuine log for completed work, not earlier calendar estimates.

## Before submission — OWNER ACTION REQUIRED

Confirm exact Codex model, write/approve ten personal essay sentences, review current acceptance/limits, authorize any desired newPRs/merges and employer private access, rehearse demo and decide delivery. Owner says not to send email. Keep private visibility. Missing inputs are not fabricated product tests.

## Bounded engineering follow-up

| Work | Why / prerequisite |
|---|---|
| Full state-transition timeline | Additional owner scope beyond incident/check journal; define edit/pause/resume audit semantics |
| Management pagination/global counters beyond500 | Current loaded selection is explicitly labeled; measure next fleet size |
| Structured API logs | Worker/dispatcher JSON already; define bounded request/correlation fields without leaking secrets |
| Controlled TLS/certificate fixture | Strengthen live SNI/cert verification evidence; keep outbound policy intact |
| Dense-history sort/index tuning | Warm p95867ms, max1.180s; preserve no-data/coverage semantics and benchmark before changes |
| Manual screen-reader/WCAG review |12axe scans/keyboard are scoped evidence, not certification |

## Before internet-facing production

Authenticated/authorized management, dedicated least-privilege public DB role, TLS ingress/rate/SSE budgets, egress controls, backups/restore drills, owner-approved retention and externalSMTP credentials/provider tests. No production-ready claim. Exact-once physicalSMTP cannot be promised merely by an outbox.

## Optional later product ideas

Additional channels, roles/teams, incident acknowledgement/escalation, certificate/DNS checks, exports and multiregion checks only with explicit user need and acceptance rules. Redis/Celery/Kubernetes, billing and speculative abstractions remain unjustified by this take-home scope. No scheduled future work is implied.
