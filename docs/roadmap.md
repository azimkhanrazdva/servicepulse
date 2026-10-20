# ServicePulse roadmap (planning, not completed history)

As of system date 2026-10-20. Deadline 2026-10-26. Keep P0 ahead of visual polish/P2.
No autonomous work after a session ends is implied. Read progress.md for actual current state.

## P0 — before Mad Devs acceptance

| Work | Value / remaining risk | Dependencies / next verification |
| --- | --- | --- |
| Confirmed DOWN/recovery correction | Avoid losing required mail on dispatcher delay | 0006 + real SMTP/order/retry/crash evidence; disclose legacy unknown eligibility and finite retry |
| Worker/public/analytics correctness | No expired claim starts; no PAUSED freshness pollution or fabricated gaps | DB tables, lease regression, actual32s and new analytics edge tests |
| 50x30 load, resource completeness | Demonstrate slow/fast independence without synthetic HTTP | Five-minute isolated harness, worker/backend/DB resource samples, browser rendering |
| Monthly history budget | Bound payload/query cost with honest dataset distribution | Synthetic10k/100k/500k/1m fleet +100k single-monitor; repeated timings/plans |
| Faults while50 monitors active | Confirm recovery under realistic mixed concurrency | Separate controlled worker/backend/DB/simulator interruption; current isolated small-fleet fault proof is narrower |
| Security acceptance | Prevent SSRF/leaks, review dependencies/history | Existing pinned-IP guards/public projections; Host guard; complete audit and dependency scan |
| Exact commit CI and full regression | Clean checkout reproducibility | Completed-stage private push only, then actual Actions/backend/browser reports; no auto-PR/merge |
| Employer acceptance/documentation | Reviewer can verify24 behavior groups | Current matrix, known limits, authentic logs/prompts, owner model confirmation/essay/access |

## P1 — requested Phase6 professional polish

| Work | Value / complexity | Risk / dependency |
| --- | --- | --- |
| Unified white/black tokens and all screens | Cohesive operations UI / medium | Replace existing colors in place, no conflicting third global theme |
| Search/status/group filters and honest sort scope | Find problems quickly / medium | Fix <=500 total-label boundary; preserve actual backend data |
| Monitor modal/drafts/delete confirmation | Clear workflows / medium | Focus return, Escape, 409 preservation, real actions |
| Notification delivery view | Diagnose pending/retry/failure / small | Reuse safe existing API; no fabricated RETRY state |
| Coverage beside sample uptime | Avoid misleading100% / small | Explain low coverage and actual gaps |
| Public page/copy/preview | Owner-controlled sharing / medium | Preserve separate bundle/routes/consent/privacy |
| Responsive/accessibility | Usable390/768/1440/1920 layouts / medium | Strict viewport test, keyboard-only flow, automatic accessibility checks, screenshots |
| Request deadlines and selected navigation | Honest loading and location / small | Safe retries and draft retention; no forever-loading fetch |
| Documentation and demonstration | Fast reviewer onboarding / small | Correspond to actual delivered code/tests; no future evidence |

## P2 — evaluate after submission, implement only with new scope

| Feature | Benefit | Complexity / risk | Dependencies / suitable time |
| --- | --- | --- | --- |
| Authentication | Safe management outside localhost | Medium; account/session security | Before any public management deployment |
| Roles/RBAC | Separate viewer/operator/admin | Medium; authorization bypass | Authentication + explicit privilege model |
| Telegram/Slack/webhook | More delivery channels | Medium; retries/secrets/egress | Generalize proven outbox only when a channel is requested |
| Production SMTP | External mailbox delivery | Medium; TLS/auth/provider limits | Owner-approved credentials/deployment, never secrets in chat |
| Multiregion checks | Regional availability evidence | High; clocks/distributed decisions | Operational need and measured single-worker ceiling |
| SSL expiry checks | Proactive certificate alerts | Medium; TLS semantics | Distinct check type and controlled TLS tests |
| DNS monitoring | Detect resolver/record changes | Medium; ambiguous propagation | Distinct policy and DNS test infrastructure |
| SLA/SLO dashboards | Reliability reporting | High; valid denominator/coverage | Define business semantics before promising SLA |
| Incident acknowledgement | Operator ownership | Medium; concurrent audit trail | Authentication + persisted actor identity |
| Escalations | Route persistent incidents | High; notification storms | Acknowledgement + proven outbox channel policies |
| API keys | Controlled automation access | Medium; rotation/leak risk | Authentication/rate limits/audit |
| Organizations/teams | Tenant separation | High; cross-tenant leaks | RBAC and strict ownership constraints |
| Billing/subscriptions | Commercial operations | High; payment/legal scope | Only if product becomes commercial |
| Hundreds/thousands of monitors | Larger fleet | High; scheduling/DB/API ceilings | Measured bottlenecks; do not add broker speculatively |
| Retention policies | Predictable storage | Medium; destructive deletion | Owner-approved retention and export/backups |
| History partitioning | Maintenance at scale | Medium/high; migration risk | Actual table/query growth and query plans |
| CSV/JSON export | Share observations | Small/medium; private data leakage | Explicit admin-only scope and bounded streaming |
| Audit logs | Accountable operations | Medium; storage/secret minimization | Actor identities and retention decisions |
| Advanced alert rules | More specific detection | High; state explosion | Documented rule semantics and deterministic tests |

## Remaining calendar plan (estimates only)

- October20: finish first reliability checkpoint and document actual experiments/review findings.
- October21–22: remaining load/fault/security acceptance and any evidenced fixes; verify history budget.
- October23: monochrome tokens, dashboard/forms/public and notification diagnostics.
- October24: four viewport/keyboard/accessibility/visual review, full browser and integration regression.
- October25: exact-commit CI, acceptance audit, limitations/readme/demo and owner review.
- October26: owner essay/model confirmation, employer private access and approved submission.

If P0 checks fail, move optional polish rather than silently reducing assertions or inventing success.
Owner controls repository visibility, PR creation/merge and final submission.
