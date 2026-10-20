# Phase6 security review — 2026-10-20 continuation

Scope: trusted-local Compose, FastAPI/React, outbound HTTP, standalone public API/build/nginx, new frontend requests and SQL optimization. Source review plus actual PostgreSQL/Chromium/Host/dependency tests. This is not a penetration test or authorization for internet-facing management.

No new confirmed BLOCKER/HIGH found in this scope. Prior notification and expired-claim correctness findings remain corrected. Independent frontend follow-up found no public API import/projection regression.

| Area | Inspected protection / evidence | Limits |
|---|---|---|
| SSRF | app/security.py validates URL/all DNS answers; numeric pinning and original Host/SNI. app/checker.py bounds time/body, rejects redirects/compression. worker disables environment proxy trust; regression covers policy/checks |Exact simulator origin is opt-in; no egress firewall. Real external TLS diversity not newly exercised |
| Public isolation | app/public.py only registers public routes; explicit fields/publication IDs, consent on every read/tick, read-only transactions and generic503. Browser tests check hidden names/URLs/recipients, revocation, REST/SSE/management isolation |Shared DB role remains privileged; add a dedicated role before production |
| Management | Loopback binding, TrustedHost and nginx host allowlist. Actual8 GET cases returned expected200/400 |Authentication intentionally absent per assignment; Host validation is not user authorization. Do not expose management publicly |
| Browser/XSS | React escaping; source search found no dangerous HTML/eval/secret storage. Public entry imports no admin panels/API; CSP/no-store retained |No browser-extension/local-malware protection claim |
| SQL | Parameter-bound input; literal SET LOCAL jit=off affects containing transaction only; public read-only regression passes |No ingress rate/SSE limits; exhaustion controls remain production work |
| Dependencies |Fresh npm/pinned-Python scans0 known vulnerabilities; axe is test-only |Advisories can change; scans do not prove absence of every vulnerability |
| Data/secrets |.env ignored; no real secret requested. Limited Git-content scan before commit; unique test projects retain volumes; owner Demo configuration preserved |Pattern scan is incomplete; no third-party secret upload |

Priorities after submission: authenticated deployment/TLS boundary, separate public DB role, connection/rate budgets and network egress policy. SMTP duplication after acceptance-before-ack remains possible; logical outbox deduplication is tested. Artifacts use disposable simulator targets/local recipients. No universal security certification.
