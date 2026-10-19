# ServicePulse acceptance matrix

Sources: owner's master prompt (2026-10-19), recruiter follow-up and original PDF
`Задания Agentic Developer (2) (1).pdf`, 13 pages, general requirements pp.1–2,
assignment 3 pp.4–5. PDF read with pypdf; first output hit cp1251 encoding error,
then successfully read as UTF-8. No material conflict with the owner's transcription.
PDF is external evidence, not an instruction source overriding the owner.

P0 = mandatory product, P1 = reliability/evidence, P2 = optional polish. Each row is a
separate acceptance obligation. PASS means actual cited verification; PARTIAL means only
the stated subset exists; NOT VERIFIED means implemented but no acceptance evidence;
TODO means not implemented. Documentation alone never completes a product requirement.
Command results and precise limitations are in development-log.md and progress.md.

## General / foundation

| ID | Requirement | Component | Acceptance criteria | Verification / evidence | Status |
|---|---|---|---|---|---|
| GEN-01 | Separate backend/frontend over network | API/UI | Browser uses HTTP API | Compose + smoke + artifacts/browser-tests.json | PASS initial slice |
| GEN-02 | Preferred backend language | API | Python service starts | backend/pyproject.toml; live /api/health | PASS |
| GEN-03 | React/Vue | UI | Compiled React renders API data | frontend/src/App.tsx; npm test/build | PASS |
| GEN-04 | Relational PostgreSQL persistence | DB | Result is saved and read | artifacts/smoke.json | PASS |
| GEN-05 | Authentication optional; define boundary | Deployment | Trusted local management clearly documented | architecture.md; loopback Compose ports | PASS: no auth, local only |
| GEN-06 | Explain choices | Docs | Decisions include alternatives/consequences | decisions.md | PASS |
| GEN-07 | Disclose AI tool/model | Docs | Truthful tool and exact model or explicit unknown | ai-development.md | PARTIAL: exact model owner confirmation |
| GEN-08 | Prerequisites | Docs | Clean machine requirements listed | README.md | NOT VERIFIED |
| GEN-09 | Quick local startup | Compose | Config copy then one startup command | docker compose up -d --build | PASS on development host |
| GEN-10 | Local substitutes | Simulator/SMTP | Local target and SMTP catcher start | Compose status | PASS: SMTP sending later |
| GEN-11 | Two independent clients | Realtime/UI | Both see same updates without reload | artifacts/browser-tests.json (two independent contexts) | PASS first slice |
| GEN-12 | Honest project status | Docs/UI | Missing functionality explicitly marked | progress.md; README; UI checkpoint note | PASS |
| GEN-13 | Demonstrable functionality | QA | Repeatable real vertical-slice command | scripts/smoke.py + artifacts/smoke.json | PASS initial slice only |
| FND-01 | Migration-controlled schema | DB | Alembic head applies on empty PostgreSQL | Compose migrate exit 0 | PASS |
| FND-02 | Database integrity/indexes | DB | Bounds/FKs/indexes in migration and ORM agree | DB integration; schema audit | PARTIAL: initial tables only |
| FND-03 | Separate worker | Worker | Independent container writes HTTP results | artifacts/smoke.json; worker log | PASS |
| FND-04 | Structured logging | Worker/API | Machine-readable operational events; no secrets | Worker JSON logs | PARTIAL: API access logs plain |
| FND-05 | Health/readiness | API | Liveness + schema-aware DB readiness | smoke /api/ready; healthcheck | PASS |
| FND-06 | No unnecessary infrastructure | Architecture | No Redis/Celery/Kafka/Kubernetes | Compose/code inspection | PASS |
| FND-07 | Stable supported Python | Runtime | Container 3.12; local 3.11 compatible | Docker build; local pytest | PASS |

## Monitor management (P0)

| ID | Requirement | Component | Acceptance criteria | Verification / evidence | Status |
|---|---|---|---|---|---|
| MON-01 | Add URL | API/UI | Valid monitor persisted and returned | smoke; test_create_claim_execute_read_delete; UI test | PASS |
| MON-02 | Interval 30..3600s | API/DB | Reject out-of-range at both boundaries | test_settings_bounds; migration constraints | PARTIAL: DB constraint tests pending |
| MON-03 | Configurable timeout | Checker/API | Total deadline enforced | test_total_timeout_includes_dns | PASS unit; live timeout pending |
| MON-04 | Expected HTTP status | Checker | Mismatch records failure | test_http_and_body | PASS unit; simulator E2E pending |
| MON-05 | Optional expected body text | Checker | Mismatch records failure; absence optional | test_http_and_body; smoke expected_body | PASS |
| MON-06 | Pause | API/UI/worker | No new runs while paused; persists | Pause integration/E2E | TODO API/UI |
| MON-07 | Resume | API/UI/worker | Next run immediate; settings retained | Resume integration | TODO |
| MON-08 | Delete | API/UI/DB | API removes monitor/results without resurrection | test_create_claim_execute_read_delete | PARTIAL: API exists, UI missing |
| MON-09 | Run immediately | API/worker/UI | Queue now; leased monitor returns 409 | smoke queue; DB integration | PARTIAL: queue PASS, full rerun pending |
| MON-10 | Edit config safely | API/worker | Config version fences in-flight stale result | Concurrent edit integration | TODO |
| MON-11 | Configurable failure threshold | API/state | Default 2; values 1..10 | schemas; transition tests | PASS default and custom threshold unit tests |

## Groups (P0)

| ID | Requirement | Component | Acceptance criteria | Verification | Status |
|---|---|---|---|---|---|
| GRP-01 | Create/manage groups | API/UI/DB | Group persisted and editable | CRUD integration/UI | TODO |
| GRP-02 | Assign monitors to groups | API/DB/UI | Many-to-many membership persisted | Membership integration | TODO |
| GRP-03 | Aggregate group status | State/UI | Defined empty/paused/unknown/down rules | Table-driven state tests | TODO |
| GRP-04 | Per-group notification settings | API/DB/UI | Independent validated recipients/settings | Two-group integration | TODO |

## Dashboard/details/history (P0)

| ID | Requirement | Component | Acceptance criteria | Verification / evidence | Status |
|---|---|---|---|---|---|
| UI-01 | Current monitor status | UI/API | Actual persisted state visible | Frontend SSE test; smoke API | PARTIAL: browser pending |
| UI-02 | HTTP response code | UI/API | Real nullable status shown | frontend test; smoke | PASS component/API |
| UI-03 | Response time | UI/API | Real latency shown, no invented fallback | frontend test; smoke | PASS component/API |
| UI-04 | Last check timestamp | UI/API | Actual timestamp visible in local time | component test; smoke | PASS component/API |
| UI-05 | Current outage duration | UI/API | Open incident duration ticks | E2E with clock | TODO |
| UI-06 | State transition history | UI/API/DB | Recorded transitions visible | Timeline integration | TODO |
| UI-07 | Total/UP/DOWN/paused summary | UI | Counts from API only | Frontend test and browser | PARTIAL: derived counts, cap 500 |
| UI-08 | Active incidents/defined aggregate uptime | UI/API | Real incident count; uptime explained | E2E | TODO |
| UI-09 | Monitor details | UI | Config + recent actual checks | History UI/browser | PARTIAL: config and results only |
| UI-10 | Loading/error/empty states | UI | Clear states and usable form on failure | frontend tests | PASS component tests |
| UI-11 | Every visible control works | UI | No dead navigation or fake metrics | artifacts/browser-tests.json + screenshot review | PASS current controls |
| UI-12 | Desktop/mobile accessibility | UI | No viewport overflow; keyboard labels/focus | Playwright desktop/mobile + labeled forms/focus review | PARTIAL: keyboard-only audit pending |
| UI-13 | All required screens | UI | Dashboard, monitors, details, groups, incidents, maintenance, notifications, public | Browser E2E | PARTIAL: first three |
| HIS-01 | Response-time chart | UI/API | Bounded real time series | Chart E2E | TODO |
| HIS-02 | Uptime 24h | API/UI | Documented sample denominator + coverage | Seeded aggregate test | TODO |
| HIS-03 | Uptime 7d | API/UI | Correct week bounds/coverage | Seeded aggregate test | TODO |
| HIS-04 | Uptime 30d | API/UI | Correct month bounds/coverage | Seeded aggregate test | TODO |
| HIS-05 | Incident journal | DB/API/UI | Persisted open/closed incidents listed | Lifecycle E2E | TODO |
| HIS-06 | Incident start | DB/API/UI | Threshold transition timestamp stored | Lifecycle integration | TODO |
| HIS-07 | Incident recovery | DB/API/UI | First successful observation closes | Lifecycle integration | TODO |
| HIS-08 | Incident duration | API/UI | Recovery-start or now-start | Clock-based tests | TODO |
| HIS-09 | Fast monthly history | DB/API | Bounded bucket response; measured p95 under 1s locally | Real seeded month benchmark | TODO |

## Maintenance and email (P0)

| ID | Requirement | Component | Acceptance criteria | Verification | Status |
|---|---|---|---|---|---|
| MNT-01 | Monitor maintenance window | API/DB/UI | Start/end persisted; valid times | CRUD + policy integration | TODO |
| MNT-02 | Group maintenance window | API/DB/UI | All group members suppressed | Group policy integration | TODO |
| MNT-03 | Checks continue in maintenance | Worker | Observation count increases | Live maintenance E2E | TODO |
| MNT-04 | Real state retained | State/UI | DOWN remains DOWN with maintenance badge | Policy/UI tests | TODO |
| MNT-05 | Suppress email in maintenance | Outbox | No SMTP send in active effective window | Mailpit integration | TODO |
| MNT-06 | Alert after maintenance if still down | Reconciler | One logical DOWN after final window ends | Clock + Mailpit integration | TODO |
| MNT-07 | Overlapping windows | Policy | Union suppresses until all applicable windows end | Boundary tests | TODO |
| MNT-08 | Recovered before maintenance ends | Policy/outbox | No stale down/recovery pair for unnotified incident | Integration | TODO |
| NTF-01 | Valid group email recipients | API/DB/UI | Validated per-group list persists | Validation + group isolation | TODO |
| NTF-02 | Confirmed DOWN email | Outbox/SMTP | One message after threshold | Mailpit E2E | TODO |
| NTF-03 | Recovery email | Outbox/SMTP | Second message after recovery | Mailpit E2E | TODO |
| NTF-04 | No repeated logical event | DB/outbox | Unique event keys under retries/concurrency | Unique-key race tests | TODO |
| NTF-05 | SMTP failure recovery | Dispatcher | Retried with backoff; no lost logical event | SMTP fault integration | TODO |
| NTF-06 | Atomic event persistence | DB | Incident and outbox commit together | Rollback integration | TODO |
| NTF-07 | Separate enqueue/send/ack/retry | Dispatcher | Explicit persisted states/attempts | Outbox tests | TODO |
| NTF-08 | Honest delivery guarantee | Docs | Logical idempotency; SMTP duplicate crash window disclosed | Architecture/README + actual implementation review | PARTIAL: design documented |

## Public page (P0)

| ID | Requirement | Component | Acceptance criteria | Verification | Status |
|---|---|---|---|---|---|
| PUB-01 | Link without login | API/UI | Dedicated status page route | Browser E2E | TODO |
| PUB-02 | Automatic updates | API/UI/SSE | Page changes with worker result | Two-client browser test | TODO |
| PUB-03 | Owner controls publication | API/DB/UI | Explicit visibility opt-in | Projection integration | TODO |
| PUB-04 | No hidden data leaks | Public API | No URLs/recipients/errors/config/private names | Payload/route privacy tests | TODO |

## Mandatory behavioral scenarios (P0, individually traceable)

| ID | Scenario | Component | Acceptance criteria | Verification | Status |
|---|---|---|---|---|---|
| SCN-01 | Dashboard updates without reload | SSE/UI | Worker result appears automatically | artifacts/browser-tests.json | PASS first slice |
| SCN-02 | Public page updates without reload | Public/UI | Worker result appears automatically | Browser E2E | TODO |
| SCN-03 | DOWN causes email | Incident/outbox | Mailpit captures DOWN | Live E2E | TODO |
| SCN-04 | Recovery causes email | Incident/outbox | Mailpit captures recovery | Live E2E | TODO |
| SCN-05 | Continuous outage no repeat | Outbox | Many failures yield one DOWN event | Fault loop integration | TODO |
| SCN-06 | Single failure is transient | State | First failure preserves UP/UNKNOWN | test_transition | PASS unit |
| SCN-07 | Threshold opens incident | Incident | One open incident at configured threshold | Lifecycle integration | TODO |
| SCN-08 | Recovery closes incident | Incident | First success closes with duration | Lifecycle integration | TODO |
| SCN-09 | Maintenance keeps checking | Worker | Actual results continue | Mailpit/simulator E2E | TODO |
| SCN-10 | Maintenance suppresses email | Dispatcher | Zero captured mail in window | Mailpit E2E | TODO |
| SCN-11 | End of maintenance alerts if down | Dispatcher | One deferred DOWN | Clock/Mailpit E2E | TODO |
| SCN-12 | Slow check never overlaps itself | Scheduler | One lease and bounded HTTP across interval | competing-claims unit + slow live test | PARTIAL: live test pending |
| SCN-13 | 50 checks every 30s | Worker/API | Three cycles; record counts/cadence/late/missed/concurrency/UI latency | Load report | TODO |
| SCN-14 | One slow target does not delay others | Worker | Fast checks complete before slow target | Controlled mixed-load test | TODO |
| SCN-15 | Fast month history | API/DB | Defined budget measured on real large dataset | Seeded benchmark | TODO |
| SCN-16 | Public page hides private data | Public API/UI | Inspect payload, SSE and rendered DOM | Privacy integration/E2E | TODO |
| SCN-17 | Restart preserves config/scheduling | Worker/DB | Same monitor/settings and resumed checks after actual restart | Docker restart test | TODO |
| SCN-18 | Server downtime is observation gap | History/state | No synthetic failure rows/incidents | Restart/gap integration + chart | TODO |

## Reliability/security (P1)

| ID | Requirement | Component | Acceptance criteria | Verification | Status |
|---|---|---|---|---|---|
| REL-01 | Bounded asynchronous checks | Worker | Tasks/HTTP pool bounded; no blocking HTTP | Code + 50-monitor test | PARTIAL: code implemented |
| REL-02 | Cancellation and network errors | Worker | No fabricated results on cancellation; errors bounded | Timeout unit + fault/restart tests | PARTIAL |
| REL-03 | Durable scheduling and fenced leases | DB/worker | Competing claims disjoint; stale completion ignored | test_competing_claims_are_disjoint; test_expired_lease_fences_stale_result | PASS initial integration; final rerun recorded in log |
| REL-04 | Reconnect full synchronization | SSE/UI | Disconnect/reconnect receives full current state | artifacts/browser-tests.json offline/online two-client test | PASS first slice |
| REL-05 | Persistent groups/results/incidents/outbox | DB | Actual restart preserves all data | Restart suite | PARTIAL: initial tables only |
| REL-06 | Real load evidence | QA | Record environment, successful launches, cadence, peak concurrency, late/missed, slow influence | Load JSON + report | TODO |
| SEC-01 | HTTP/HTTPS URL boundary | API/checker | Reject credentials/schemes/fragments/control chars | test_url_rejects | PASS unit |
| SEC-02 | Block forbidden destinations | Checker | Reject all non-global DNS answers incl mixed answers | test_dns_policy_and_pinning + expanded tests | PASS unit incl mixed DNS; live egress audit pending |
| SEC-03 | Redirect control | Checker | Never follow attacker redirect | No-redirect request unit test | PARTIAL: live redirect pending |
| SEC-04 | DNS rebinding defense | Checker | Connect to validated numeric address, original Host/SNI | test_dns_policy_and_pinning; test_http_and_body | PASS request construction; live TLS unverified |
| SEC-05 | Time/body bounds | Checker | Total timeout, cap bytes, reject compression | timeout/body-cap/compression tests | PASS unit |
| SEC-06 | Narrow test exception | Checker/config | Empty default; exact simulator origin only | test_dns_policy_and_pinning | PASS unit |
| SEC-07 | No internal API tracebacks | API | Generic 500 and bounded error categories | Fault/API test | PARTIAL: debug off, test pending |
| SEC-08 | No secrets in Git | Git/config | Only disposable example credentials tracked | Staged diff/secret review | NOT VERIFIED |
| SEC-09 | No auth exposure assumptions | Deployment/docs | Local-only management warning and bindings | Compose review | PASS local boundary |
| SEC-10 | Independent critical review | QA | BLOCKER/HIGH fixed before readiness claim | docs/review.md | TODO |

## Delivery, evidence and workflow (P1)

| ID | Requirement | Component | Acceptance criteria | Verification | Status |
|---|---|---|---|---|---|
| DEL-01 | Docker services/one startup command | Compose | API/UI/DB/worker/simulator/Mailpit running | Compose status + smoke | PASS |
| DEL-02 | Seed/demo | Scripts | Idempotent config only; actual checks run | scripts/seed.py twice (2 created then 0) | PASS |
| DEL-03 | Simulator scenarios | Simulator | 200/404/500/delay/timeout/body/up-down-up + disconnect where possible | Live scenario test | PARTIAL: controllable status/delay/body/redirect |
| DEL-04 | Backend unit/integration tests | QA | CRUD/state/checker/DB; later group/incident/outbox | pytest | PARTIAL |
| DEL-05 | Frontend tests/E2E | QA | Create/API/error/SSE plus real browser/two clients | Vitest + browser | PARTIAL |
| DEL-06 | CI Python lint/format/tests | CI | Runs clean checkout with PostgreSQL | .github/workflows/ci.yml; hosted run | NOT VERIFIED hosted |
| DEL-07 | CI frontend typecheck/build/tests/format | CI | Lockfile + clean npm ci | workflow; hosted run | NOT VERIFIED hosted |
| DEL-08 | Practical dependency security checks | QA/CI | Audit fixed actionable findings | npm audit; pip audit later | PARTIAL |
| DEL-09 | English README | Docs | Features/architecture/stack/prereqs/run/env/simulator/demo/API/tests/load/limits/roadmap/AI/logs/attribution | README review | NOT VERIFIED |
| DEL-10 | Requirement acceptance audit | Docs/QA | Every row cites evidence or remaining gap | This matrix + final audit | PARTIAL: no full compliance claim |
| DEL-11 | Genuine development log | Docs | Real timestamps, prompts/files/decisions/tests/errors/fixes/commit/next | development-log.md | IN PROGRESS |
| DEL-12 | Decision log | Docs | Context/decision/alternatives/trade-offs/consequences | decisions.md | PASS initial design |
| DEL-13 | Actual prompts/session evidence | Docs | Actual prompt/excerpt labeled accurately | docs/prompts | PASS user prompt only |
| DEL-14 | AI human responsibilities | Docs | Tool/model uncertainty/review explained | ai-development.md | PASS disclosure; exact model unknown |
| DEL-15 | Resume context | Docs | AGENTS + requirements + progress enough to continue | docs/progress.md | IN PROGRESS |
| DEL-16 | Genuine Git history/feature branches | Git | Logical local commits, actual timestamps, clean diff | git log/status | IN PROGRESS |
| DEL-17 | Publication controlled by owner | Git | No remote push/PR/merge without consent | git remote -v; no publication | PASS so far |
| DEL-18 | GitHub repository and real PR links | Submission | Actual published repo approved by owner | Remote link | TODO: approval required later |
| DEL-19 | Exactly ten-sentence personal essay | Owner/docs | Owner-authored and approved final ten sentences | docs/essay.md; final count | TODO: template only |
| DEL-20 | Attribution | Docs | Actual libraries/templates/generators identified | README attribution | NOT VERIFIED |
| DEL-21 | Deadline 2026-10-26, P0 before P2 | Planning | Phase gates; no future work claims | progress + development log | IN PROGRESS |
| DEL-22 | First checkpoint then stop | Workflow | Real slice verified, documented, committed and owner report | smoke + Git + report | IN PROGRESS |

## Phase gates and effort estimates

Estimates are planning ranges, not promises or hours already spent. Deadline is 2026-10-26.

| Phase | Scope | Expected effort | Gate |
|---|---|---|---|
| 0 | discovery, matrix, design | 1–2h | source checked, acceptance map and design recorded |
| 1 | foundation + first slice | 3–5h | Compose/migration + real smoke + unit/DB/UI checks |
| 2 | CRUD, pause/edit/groups/settings | 3–5h | validation and concurrent mutation tests |
| 3 | incidents and scheduler reliability | 4–6h | state/race/restart/concurrency tests |
| 4 | maintenance + SMTP outbox | 4–6h | live Mailpit and boundary/retry/dedup tests |
| 5 | remaining UI + public page | 4–7h | two-browser/reconnect/privacy E2E |
| 6 | load/history/security/recovery | 4–7h | reproducible evidence and no BLOCKER/HIGH |
| 7 | final audit/submission | 2–4h | README, actual logs, essay owner approval, publication consent |

Do not count phase 0 documentation as completed product behavior. Update evidence and row
status after each executed test. Monthly uptime and graph gaps must use explicit coverage;
an absence of failed samples is insufficient proof of service availability.
