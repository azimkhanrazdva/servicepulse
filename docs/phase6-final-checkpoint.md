# ServicePulse v0.6 — verified local checkpoint

This continuation follows the preserved partial phase6-checkpoint.md. Same feature branch; no original date/history rewritten. Actual timestamps and subsequent Git/CI outcomes are in development-log.md. Phase7 has not started; owner review is next.

## Delivered

- Prior0006 notification eligibility/obligation, expired worker/public freshness/Host corrections retained.
- Actual50-monitor fault experiment with two real clients; no repeated steady300s test. Log/persistence audit verifies no overlapping logged HTTP calls or fabricated observations in measured scope.
- Coverage/warning, honest loaded500 scope, selected navigation and bounded complete-request deadlines.
- Unified white/black admin/public UI; real filters/search/sort, safe editor dialog, delivery diagnostics and public-link copy/preview. No heavy UI dependency.
- Four viewport/keyboard/axe journeys, functional regression and public privacy checks.
- Repeated cold/warm history identified JIT cost; transaction-local JIT off preserves SQL semantics/defaults. No migration beyond0006.

## Verification

| Gate | Actual result / evidence |
|---|---|
| Backend/PostgreSQL |149 PASS; phase6-backend-tests.xml; legacy0001..0005 fixtures ->0006, Alembic check |
| Components |32 PASS; phase6-frontend-tests.json; deadlines, conflicts/draft retention, pending-save dismissal, coverage/navigation |
| Chromium |11 PASS on final build; phase6-browser-tests.json; original7 plus4 design journeys |
| Accessibility |12 axe scans,0 violations; per-width JSON retains incomplete checks. Not full WCAG/screen-reader certification |
| Real SMTP delay/refusal/retry/restart |PASS49.859s; phase6-email-continuation.json; ordered DOWN/RECOVERY and stable delivery IDs |
| Fault-under50 |Six groups PASS206.172s; phase6-fault-load.json/browser/log/log-analysis/persistence-audit |
| Monthly history |100000 rows/360 buckets,3cold/21warm; cold max635ms, warm p95867ms, max1.180s. Exact limits in performance report |
| Static/build |Ruff/check+format, TypeScript, ESLint, Prettier and production builds PASS |
| Security |Defined-boundary source/privacy/SSRF/Host review; fresh npm/pip scans0 known vulnerabilities |
| Hosted CI |Record only exact-SHA actual outcome after private upload in development-log.md |

Original checkpoint/load/history artifacts are retained. New regression files use phase6 prefixes. Resource samples, expected errors, failed attempts and measurement limits are in phase6-performance.md.

## Reproduce

On a fresh checkout prepare .env from .env.example; preserve an existing configuration. Enable only the exact simulator exception described in README for the local demo.

```powershell
docker compose up -d --build --wait
docker compose --profile test run --rm --build tests
python -m ruff check backend scripts/phase6*
python -m ruff format --check backend scripts/phase6*
cd frontend
npm ci
npx playwright install chromium
npm run typecheck
npm run lint
npm test
npm run format:check
npm run build
npm run test:e2e -- --workers=2
cd ..
python scripts/phase6_fault_load.py
python scripts/phase6_cold_history.py
python scripts/phase6_email_smoke.py
```

Run experiments sequentially: fixed ports19000/19080 or18000/18025. They create UUID test projects and retain volumes; do not use down -v or prune. HTTP completion and persistence counts differ across faults/deletion/config changes. A shutdown may persist another in-flight observation. UI http://localhost:8080, API docs http://localhost:8000/docs, Mailpit http://localhost:8025. Public root8081 intentionally404; explicitly publish a page then open /status/<slug>.

## Remaining limits and roadmap

Before26October: owner reviews v0.6; separately authorizes prepared stacked Phase5/6 PRs if desired; Phase7 acceptance/submission audit, exact model disclosure, personal ten-sentence essay, reviewer access and fresh-checkout demo. No automatic PR/merge/visibility change or Phase7 start.

After submission: dedicated public DB role/authenticated deployment, measured sort tuning, management pagination beyond500, screen-reader/WCAG2.2 review and real-provider delivery testing.

Limits: warm outlier>1s; three cold samples/OS cache/shared host; loaded500 selection; trusted-local management without auth; physical SMTP duplicate ambiguity; historical unknown notification eligibility not guessed. No universal performance/security/accessibility certification.
