# ServicePulse acceptance matrix

Sources: owner's master prompt (2026-10-19), recruiter follow-up and original PDF
`Задания Agentic Developer (2) (1).pdf`, 13 pages, general requirements pp.1–2,
assignment 3 pp.4–5. PDF read with pypdf; first output hit cp1251 encoding error,
then successfully read as UTF-8. No material conflict with the owner's transcription.
PDF is external evidence, not an instruction source overriding the owner.

P0/P1/P2 are owner project priorities, not original employer wording. See
[the per-ID provenance audit](requirements-provenance.md) for M (employer), O (owner),
T (technical criterion) and OPT (optional). The baseline has 133 project obligations; phase-specific owner additions follow below. These are not 133 PDF requirements. Each row is a
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
| GEN-08 | Prerequisites | Docs | Clean machine requirements listed | README.md reviewed against current slice | PASS documentation; full feature scope pending |
| GEN-09 | Quick local startup | Compose | Config copy then one startup command | docker compose up -d --build | PASS on development host |
| GEN-10 | Local substitutes | Simulator/SMTP | Local target and SMTP catcher start | Compose status | PASS: SMTP sending later |
| GEN-11 | Two independent clients | Realtime/UI | Both see same updates without reload | artifacts/browser-tests.json (two independent contexts) | PASS first slice |
| GEN-12 | Honest project status | Docs/UI | Missing functionality explicitly marked | progress.md; README; UI checkpoint note | PASS |
| GEN-13 | Demonstrable functionality | QA | Repeatable real vertical-slice command | scripts/smoke.py + artifacts/smoke.json | PASS initial slice only |
| FND-01 | Migration-controlled schema | DB | Alembic head applies on empty PostgreSQL | Compose migrate exit 0 | PASS |
| FND-02 | Database integrity/indexes | DB | Bounds/FKs/indexes in migration and ORM agree | DB integration; schema audit | PARTIAL: monitors/groups/results/incidents restart verified; outbox absent |
| FND-03 | Separate worker | Worker | Independent container writes HTTP results | artifacts/smoke.json; worker log | PASS |
| FND-04 | Structured logging | Worker/API | Machine-readable operational events; no secrets | Worker JSON logs | PARTIAL: API access logs plain |
| FND-05 | Health/readiness | API | Liveness + schema-aware DB readiness | smoke /api/ready; healthcheck | PASS |
| FND-06 | No unnecessary infrastructure | Architecture | No Redis/Celery/Kafka/Kubernetes | Compose/code inspection | PASS |
| FND-07 | Stable supported Python | Runtime | Container 3.12; local 3.11 compatible | Docker build; local pytest | PASS |

## Monitor management (P0)

| ID | Requirement | Component | Acceptance criteria | Verification / evidence | Status |
|---|---|---|---|---|---|
| MON-01 | Add URL | API/UI | Valid monitor persisted and returned | smoke; test_create_claim_execute_read_delete; UI test | PASS |
| MON-02 | Interval 30..3600s | API/DB | Reject out-of-range at both boundaries | test_settings_bounds; migration constraints | PASS API bounds + database constraint test |
| MON-03 | Configurable timeout | Checker/API | Total deadline enforced | test_total_timeout_includes_dns | PASS unit; live timeout pending |
| MON-04 | Expected HTTP status | Checker | Mismatch records failure | test_http_and_body | PASS unit; simulator E2E pending |
| MON-05 | Optional expected body text | Checker | Mismatch records failure; absence optional | test_http_and_body; smoke expected_body | PASS |
| MON-06 | Pause | API/UI/worker | No new runs while paused; persists | Pause integration/E2E | PASS DB/concurrent HTTP + browser + 31s live pause |
| MON-07 | Resume | API/UI/worker | Next run immediate; settings retained | Resume integration | PASS DB/browser and live worker restart |
| MON-08 | Delete | API/UI/DB | API removes monitor/results without resurrection | test_create_claim_execute_read_delete | PASS API cascade + browser confirmation/two clients |
| MON-09 | Run immediately | API/worker/UI | Queue now; leased monitor returns 409 | smoke queue; DB integration | PASS queued dedup + browser + real persisted manual check |
| MON-10 | Edit config safely | API/worker | Config version fences in-flight stale result | Concurrent edit integration | PASS version conflicts + pre/in-flight fencing + browser draft preservation |
| MON-11 | Configurable failure threshold | API/state | Default 2; values 1..10 | schemas; transition tests | PASS default and custom threshold unit tests |

## Groups (P0)

| ID | Requirement | Component | Acceptance criteria | Verification | Status |
|---|---|---|---|---|---|
| GRP-01 | Create/manage groups | API/UI/DB | Group persisted and editable | CRUD integration/UI | PASS CRUD API/DB/browser |
| GRP-02 | Assign monitors to groups | API/DB/UI | Many-to-many membership persisted | Membership integration | PASS membership API/browser/cascade/restart |
| GRP-03 | Aggregate group status | State/UI | Defined empty/paused/unknown/down rules | Table-driven state tests | PASS state table + API/browser/live UP/PAUSED/UNKNOWN |
| GRP-04 | Per-group notification settings | API/DB/UI | Independent validated recipients/settings | Two-group integration | PASS persisted validated recipients; sending deferred |

## Dashboard/details/history (P0)

| ID | Requirement | Component | Acceptance criteria | Verification / evidence | Status |
|---|---|---|---|---|---|
| UI-01 | Current monitor status | UI/API | Actual persisted state visible | Frontend SSE test; smoke API | PASS live two-browser snapshots |
| UI-02 | HTTP response code | UI/API | Real nullable status shown | frontend test; smoke | PASS component/API |
| UI-03 | Response time | UI/API | Real latency shown, no invented fallback | frontend test; smoke | PASS component/API |
| UI-04 | Last check timestamp | UI/API | Actual timestamp visible in local time | component test; smoke | PASS component/API |
| UI-05 | Current outage duration | UI/API | Open incident duration ticks | IncidentsPanel/OutageDuration clock tests and live dashboard E2E | PASS journal/dashboard phase5 |
| UI-06 | State transition history | UI/API/DB | Recorded transitions visible | Incident journal + observation history | PARTIAL: confirmed DOWN/closure; full state timeline later |
| UI-07 | Total/UP/DOWN/paused summary | UI | Counts from API only | Frontend test and browser | PARTIAL: derived counts, cap 500 |
| UI-08 | Active incidents/defined aggregate uptime | UI/API | Real incident count; uptime explained | Live SQL count + dashboard E2E; optional fleet uptime omitted | PASS active count; per-monitor observed uptime disclosed |
| UI-09 | Monitor details | UI | Config + recent actual checks | History UI/browser | PASS config editor + real observation history; incidents via journal filter, charts pending |
| UI-10 | Loading/error/empty states | UI | Clear states and usable form on failure | frontend tests | PASS component tests |
| UI-11 | Every visible control works | UI | No dead navigation or fake metrics | artifacts/browser-tests.json + screenshot review | PASS current controls |
| UI-12 | Desktop/mobile accessibility | UI | No viewport overflow; keyboard labels/focus | Playwright desktop/mobile + labeled forms/focus review | PARTIAL: keyboard-only audit pending |
| UI-13 | All required screens | UI | Dashboard, monitors, details, groups, incidents, maintenance, notifications, public | Functional sections/details plus separate public route; notifications reuse group recipient editor | PASS functional views |
| HIS-01 | Response-time chart | UI/API | Bounded real time series | AnalyticsPanel tests + real public.spec.ts bars/gaps/table | PASS phase5 |
| HIS-02 | Uptime 24h | API/UI | Documented sample denominator + coverage | PostgreSQL aggregate + browser + dashboard overview | PASS phase5 |
| HIS-03 | Uptime 7d | API/UI | Correct week bounds/coverage | Period-parametrized PostgreSQL test + browser | PASS phase5 |
| HIS-04 | Uptime 30d | API/UI | Correct month bounds/coverage | Dense SQL fixture, bounds/gaps and real 30d chart | PASS phase5 |
| HIS-05 | Incident journal | DB/API/UI | Persisted open/closed incidents listed | test_incident_threshold_recovery_timestamps_and_pagination; incidents.spec.ts | PASS phase3 |
| HIS-06 | Incident start | DB/API/UI | Threshold transition timestamp stored | Clock-controlled threshold test | PASS phase3 |
| HIS-07 | Incident recovery | DB/API/UI | First successful observation closes | Lifecycle DB + live phase3-smoke.json | PASS phase3 |
| HIS-08 | Incident duration | API/UI | Recovery-start or now-start | Clock-controlled DB/component tests + two-client E2E | PASS phase3 |
| HIS-09 | Fast monthly history | DB/API | Bounded bucket response; measured p95 under 1s locally | 10000 rows / one SQL / 360 buckets / 0.055304s single measurement | PARTIAL: p95/larger-dataset gate remains phase6 |

## Maintenance and email (P0)

| ID | Requirement | Component | Acceptance criteria | Verification | Status |
|---|---|---|---|---|---|
| MNT-01 | Monitor maintenance window | API/DB/UI | Start/end persisted; valid times | Maintenance CRUD API/browser + migration fixtures | PASS phase4 |
| MNT-02 | Group maintenance window | API/DB/UI | All group members suppressed | Group-route tests + live browser/group window | PASS phase4; group-specific suppression |
| MNT-03 | Checks continue in maintenance | Worker | Observation count increases | phase4-fault.json and browser: new real failed observations in maintenance | PASS phase4 |
| MNT-04 | Real state retained | State/UI | DOWN remains DOWN with maintenance badge | maintenance.spec.ts: DOWN and separate MAINTENANCE badge in two clients | PASS phase4 |
| MNT-05 | Suppress email in maintenance | Outbox | No SMTP send in active effective window | Preflight policy tests, actual Mailpit suppression; phase4-design.md boundary | PASS at authorization; in-flight SMTP cannot be recalled |
| MNT-06 | Alert after maintenance if still down | Reconciler | One logical DOWN after final window ends | phase4-fault.json: deferred DOWN with unchanged result history | PASS phase4 |
| MNT-07 | Overlapping windows | Policy | Union suppresses until all applicable windows end | test_overlapping_windows_exact_boundaries_and_reconcile_without_result | PASS phase4 |
| MNT-08 | Recovered before maintenance ends | Policy/outbox | No stale down/recovery pair for unnotified incident | Real isolated recovered-inside-window scenario and unit policy tests | PASS phase4 |
| NTF-01 | Valid group email recipients | API/DB/UI | Validated per-group list persists | Existing recipient validation + shared-address route/isolation tests + UI | PASS phase4 |
| NTF-02 | Confirmed DOWN email | Outbox/SMTP | One message after threshold | Actual Mailpit SMTP/API: normal DOWN and maintenance release | PASS phase4 |
| NTF-03 | Recovery email | Outbox/SMTP | Second message after recovery | Actual normal and deferred recovery captured by Mailpit | PASS phase4 |
| NTF-04 | No repeated logical event | DB/outbox | Unique event keys under retries/concurrency | DB event/delivery unique constraints, repeated checks, competing claims | PASS phase4; logical dedup |
| NTF-05 | SMTP failure recovery | Dispatcher | Retried with backoff; no lost logical event | phase4-fault.json: stopped Mailpit, persisted retry, dispatcher restart | PASS phase4 |
| NTF-06 | Atomic event persistence | DB | Incident and outbox commit together | test_event_constraints_and_atomic_rollback: actual PostgreSQL error | PASS phase4 |
| NTF-07 | Separate enqueue/send/ack/retry | Dispatcher | Explicit persisted states/attempts | Delivery claim/preflight/send/ack/backoff/expiry/cancellation tests | PASS phase4 |
| NTF-08 | Honest delivery guarantee | Docs | Logical idempotency; SMTP duplicate crash window disclosed | Actual acceptance crash: 3 physical messages, 2 logical deliveries; design/README | PASS disclosed and measured |

## Public page (P0)

| ID | Requirement | Component | Acceptance criteria | Verification | Status |
|---|---|---|---|---|---|
| PUB-01 | Link without login | API/UI | Dedicated status page route | Real /status/{slug} on public-only 8081, no credentials | PASS phase5 |
| PUB-02 | Automatic updates | API/UI/SSE | Page changes with worker result | Two real public clients, worker DOWN/UP/reconnect | PASS phase5 |
| PUB-03 | Owner controls publication | API/DB/UI | Explicit visibility opt-in | Disabled/empty default, explicit labels/history, live revocation | PASS phase5 |
| PUB-04 | No hidden data leaks | Public API | No URLs/recipients/errors/config/private names | Exact keys/sentinels/route-method isolation, safe SSE, generic errors | PASS tested public surface; final security review later |

## Mandatory behavioral scenarios (P0, individually traceable)

| ID | Scenario | Component | Acceptance criteria | Verification | Status |
|---|---|---|---|---|---|
| SCN-01 | Dashboard updates without reload | SSE/UI | Worker result appears automatically | artifacts/browser-tests.json | PASS first slice |
| SCN-02 | Public page updates without reload | Public/UI | Worker result appears automatically | public.spec.ts two real clients and worker DOWN/UP/reconnect | PASS phase5 |
| SCN-03 | DOWN causes email | Incident/outbox | Mailpit captures DOWN | phase4-fault.json + phase4-browser-mail.json | PASS phase4 Mailpit |
| SCN-04 | Recovery causes email | Incident/outbox | Mailpit captures recovery | phase4-fault.json + phase4-browser-mail.json | PASS phase4 Mailpit |
| SCN-05 | Continuous outage no repeat | Outbox | Many failures yield one DOWN event | Repeated actual failures retain one DOWN message and one event/address | PASS logical/normal SMTP path; crash duplicate documented |
| SCN-06 | Single failure is transient | State | First failure preserves UP/UNKNOWN | test_transition | PASS unit |
| SCN-07 | Threshold opens incident | Incident | One open incident at configured threshold | DB uniqueness/competing completion + live smoke | PASS phase3 |
| SCN-08 | Recovery closes incident | Incident | First success closes with duration | DB clock test + real simulator recovery | PASS phase3 |
| SCN-09 | Maintenance keeps checking | Worker | Actual results continue | Actual observations continue while monitor remains DOWN/maintenance | PASS phase4 |
| SCN-10 | Maintenance suppresses email | Dispatcher | Zero captured mail in window | Actual Mailpit zero messages in controlled active window | PASS at authorization boundary; in-flight caveat disclosed |
| SCN-11 | End of maintenance alerts if down | Dispatcher | One deferred DOWN | Reconciliation releases after end with no new CheckResult | PASS phase4 |
| SCN-12 | Slow check never overlaps itself | Scheduler | One lease and bounded HTTP across interval | phase3-smoke.json: real 32s HTTP / 30s interval; lease race tests | PASS within documented lease fault model; arbitrary suspension beyond expiry excluded |
| SCN-13 | 50 checks every 30s | Worker/API | Three cycles; record counts/cadence/late/missed/concurrency/UI latency | Load report | TODO |
| SCN-14 | One slow target does not delay others | Worker | Fast checks complete before slow target | phase3-smoke.json: fast result during real 32s request | PASS phase3 mixed pair; 50-load separate |
| SCN-15 | Fast month history | API/DB | Defined budget measured on real large dataset | Bounded SQL, 10000-row fixture single measurement | PARTIAL: full performance gate phase6 |
| SCN-16 | Public page hides private data | Public API/UI | Inspect payload, SSE and rendered DOM | DB allowlist + native public SSE and real DOM/route E2E | PASS phase5 |
| SCN-17 | Restart preserves config/scheduling | Worker/DB | Same monitor/settings and resumed checks after actual restart | phase2/phase3-smoke.json | PASS actual restart for monitors/groups/incidents |
| SCN-18 | Server downtime is observation gap | History/state | No synthetic failure rows/incidents | Rerun phase3 gap; SQL gap/legacy tests; real NO_DATA chart and periodic refresh regression | PASS phase5 combined evidence |

## Reliability/security (P1)

| ID | Requirement | Component | Acceptance criteria | Verification | Status |
|---|---|---|---|---|---|
| REL-01 | Bounded asynchronous checks | Worker | Tasks/HTTP pool bounded; no blocking HTTP | Code + 50-monitor test | PARTIAL: code implemented |
| REL-02 | Cancellation and network errors | Worker | No fabricated results on cancellation; errors bounded | Timeout unit + fault/restart tests | PARTIAL |
| REL-03 | Durable scheduling and fenced leases | DB/worker | Competing claims disjoint; stale completion ignored | test_competing_claims_are_disjoint; test_expired_lease_fences_stale_result | PASS initial integration; final rerun recorded in log |
| REL-04 | Reconnect full synchronization | SSE/UI | Disconnect/reconnect receives full current state | artifacts/browser-tests.json offline/online two-client test | PASS first slice |
| REL-05 | Persistent groups/results/incidents/outbox | DB | Actual restart preserves all data | phase2/3 restart smoke + phase4 isolated DB/dispatcher/worker restart and same outbox ID | PASS covered persisted entities |
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
| DEL-06 | CI Python lint/format/tests | CI | Runs clean checkout with PostgreSQL | .github/workflows/ci.yml; hosted run | PASS hosted run 39319384324 on 034b4bd |
| DEL-07 | CI frontend typecheck/build/tests/format | CI | Lockfile + clean npm ci | workflow; hosted run | PASS hosted run 39319384324 on 034b4bd |
| DEL-08 | Practical dependency security checks | QA/CI | Audit fixed actionable findings | npm audit; pip audit later | PARTIAL |
| DEL-09 | English README | Docs | Features/architecture/stack/prereqs/run/env/simulator/demo/API/tests/load/limits/roadmap/AI/logs/attribution | README review | PASS reviewed against v0.3 scope |
| DEL-10 | Requirement acceptance audit | Docs/QA | Every row cites evidence or remaining gap | This matrix + final audit | PARTIAL: no full compliance claim |
| DEL-11 | Genuine development log | Docs | Real timestamps, prompts/files/decisions/tests/errors/fixes/commit/next | development-log.md actual session + commit | PASS first checkpoint |
| DEL-12 | Decision log | Docs | Context/decision/alternatives/trade-offs/consequences | decisions.md | PASS initial design |
| DEL-13 | Actual prompts/session evidence | Docs | Actual prompt/excerpt labeled accurately | docs/prompts | PASS user prompt only |
| DEL-14 | AI human responsibilities | Docs | Tool/model uncertainty/review explained | ai-development.md | PASS disclosure; exact model unknown |
| DEL-15 | Resume context | Docs | AGENTS + requirements + progress enough to continue | docs/progress.md with continuation instructions | PASS first checkpoint |
| DEL-16 | Genuine Git history/feature branches | Git | Logical local commits, actual timestamps, clean diff | local 4f212d9 and documentation follow-up; git log/status | PASS first checkpoint |
| DEL-17 | Publication controlled by owner | Git | No remote push/PR/merge without consent | Private origin; authorized stage pushes and later expressly requested PRs #1/#2/#3; no merge | PASS |
| DEL-18 | GitHub repository and real PR links | Submission | Actual published repo approved by owner | github-workflow.md links private repo and actual PRs #1/#2/#3 | PARTIAL: repo/PRs published privately; employer access/submission pending |
| DEL-19 | Exactly ten-sentence personal essay | Owner/docs | Owner-authored and approved final ten sentences | docs/essay.md; final count | TODO: template only |
| DEL-20 | Attribution | Docs | Actual libraries/templates/generators identified | README attribution | PASS README attribution reviewed |
| DEL-21 | Deadline 2026-10-26, P0 before P2 | Planning | Phase gates; no future work claims | progress + development log | IN PROGRESS |
| DEL-22 | First checkpoint then stop | Workflow | Real slice verified, documented, committed and owner report | artifacts/checkpoint.json + local Git + owner report | PASS first checkpoint |

## Phase 3 owner acceptance additions

These are owner/engineering criteria from prompts/003-phase3.md, not extra employer PDF requirements.

| ID | Requirement/component | Acceptance criterion | Executed evidence | Status |
|---|---|---|---|---|
| INC-01 | Threshold/worker | Default 2 failures; first preserves UP, repeated failures retain ID | Clock DB lifecycle + live smoke | PASS |
| INC-02 | Recovery/worker | First success closes; repeated success adds no incident | DB lifecycle + live/browser recovery | PASS |
| INC-03 | Migration/DB | 0002 DOWN/settings/results/groups/recipients preserved, no inferred events | tests/run.py legacy fixtures + Alembic check | PASS |
| INC-04 | Integrity/DB | One open incident; valid closure timestamps/reasons | Partial unique/check constraints + direct invalid insert tests | PASS |
| INC-05 | Atomicity/worker | DB save fault leaves no partial transition/result/incident | Real SELECT 1/0 rollback and lease recovery test | PASS |
| INC-06 | Pause/resume/API | PAUSED admin closure, no recovery; resume UNKNOWN/new threshold | Parameterized administrative closure test | PASS |
| INC-07 | Edit/delete/API | CONFIG_CHANGED admin closure; stale results discarded; delete cascades | Administrative + stale-success/failure race tests | PASS |
| INC-08 | Journal/API | Filter monitor/state/time, order, pagination, bounded validation, 404 | DB API tests, 150-row one-query test | PASS |
| INC-09 | Duration/API/UI | UTC confirmation/recovery times; closed duration fixed, open ticking | Clock DB/component tests + browser | PASS |
| INC-10 | Realtime/SSE/UI | Two clients see open/closed; reconnect synchronizes | incidents.spec.ts + original reconnect E2E | PASS |
| INC-11 | Fault fencing/worker | Old expiry return/retried completion cannot duplicate/close newer incident | DB gated races and competing claims | PASS |
| INC-12 | Slow checks/worker | >interval HTTP has no ordinary overlap; fast target completes | Actual 32s/30s live smoke + deterministic cancellation test | PASS within documented fault model |
| INC-13 | Restart/DB/worker | Incident ID/config survive actual restart; no gap backfill | phase3-smoke.json | PASS |
| INC-14 | Future notifications/model | Confirmed UUID; recovered/admin closures distinct; proposed idempotent keys | ADR-009, architecture.md; phase4-audit.md | PASS phase3 design; outbox/SMTP now implemented and verified phase4 |
| INC-15 | Git/workflow | Branch from actual phase2; prepared stacked PR commands, no unauthorized PR/merge | pr-phase3.md; private push 5b43b20; hosted run 39323301037 | PASS private upload/CI; no PR/merge |

## Phase 4 owner acceptance additions

These are additional engineering acceptance criteria recorded in prompts/004-phase4.md,
not extra employer PDF obligations. Its identity with the available earlier attachment was
verified during the later audit; see phase4-audit.md for the owner's clarification and exact hash.
The original PDF/master prompt remain the audit baseline; no new prompt receipt is inferred.

| ID | Requirement/component | Acceptance criterion | Executed evidence | Status |
|---|---|---|---|---|
| P4-01 | Maintenance CRUD/API/UI | Create/edit/delete/list with target/version validation | DB CRUD tests, maintenance.spec.ts | PASS |
| P4-02 | Monitor window/policy | All of monitor's routes suppressed | Multi-group monitor-window test, real isolated monitor window | PASS at authorization |
| P4-03 | Group window/policy | Only that group's routes suppressed | Independent/shared-group test and live group window | PASS |
| P4-04 | Overlaps/time | UTC start inclusive/end exclusive; union until last end | Controlled clock boundaries and overlap tests | PASS |
| P4-05 | HTTP continuity/worker | Observations continue under maintenance | Real failed checks in phase4-fault.json/browser | PASS |
| P4-06 | Real DOWN/UI | DOWN retained beside badge in two clients | maintenance.spec.ts | PASS |
| P4-07 | Send suppression/dispatcher | No authorization while all applicable routes suppressed | Preflight-after-claim test; zero Mailpit messages in controlled window | PASS; in-flight boundary disclosed |
| P4-08 | End reconciliation | Deferred DOWN without new HTTP result or incident | Actual unchanged-history window-end test | PASS |
| P4-09 | Quick recovery/policy | No stale pair for an unattempted/suppressed DOWN | Real Mailpit and DB tests | PASS |
| P4-10 | Durable outbox/DB | Events/routes/deliveries stored with IDs/status/leases | Migration, DB tests, actual restart | PASS |
| P4-11 | Atomic transitions/DB | Result/state/incident/event/routes/deliveries roll back together | PostgreSQL SELECT 1/0 fault after event flush | PASS |
| P4-12 | Logical dedup/DB | Event unique per incident/type; delivery unique event/address | Direct unique-violation tests and real repeated failures | PASS |
| P4-13 | Retry/SMTP | Persist backoff, bounded attempts and permanent failure | 4xx/5xx/network/timeout/backoff tests; Mailpit outage | PASS |
| P4-14 | Dispatcher concurrency | Disjoint claims and stale-token ack rejected | Concurrent claim/expiry/cancellation tests | PASS within lease model |
| P4-15 | Restart/queue | Same delivery identity continues after process/DB restart | phase4-fault.json | PASS |
| P4-16 | Actual Mailpit | Normal DOWN/RECOVERY received, same incident, no normal repeat | Real SMTP/API and browser receipts | PASS |
| P4-17 | Maintenance editor/UI | Monitor/group selection, local-to-UTC time, editing and conflict draft | Component tests/browser | PASS |
| P4-18 | Two clients/reconnect | Active/end badges and state synchronized automatically | Real maintenance browser E2E | PASS |
| P4-19 | Regression | All original unit/component/browser scenarios retained and run | phase4-audit.md: 109 backend, 15 component, 5 browser; default-2 outbox and terminal-550 regressions added | PASS local audit |
| P4-20 | New tests | Faults actually executed, no mocked SMTP-only claim | Isolated fault report and actual Mailpit IDs | PASS |
| P4-21 | Additive migration | Preserve existing settings/history/open/closed incidents, no mass alerts | 0003 fixture comparison, notifications_enabled=false/events=0 | PASS |
| P4-22 | Honest docs | Contract, status, setup, limits and evidence match actual code | README/design/architecture/checkpoint review | PASS local; hosted result recorded after run |
| P4-23 | Authentic history | Real local commits and command timestamps; no backdating | development-log.md, actual local commit 2a159d1 | PASS |
| P4-24 | PR preparation | Correct Phase2→main, Phase3→2, Phase4→3; no unauthorized PR/merge | Actual owner-authorized PRs #1/#2/#3; gh verifies PR #3 base feat/incident-lifecycle | PASS created on later owner request; no merge |
| P4-25 | Critical review | No unexplained BLOCKER/HIGH; SMTP race/uncertainty explicit | review.md and actual acceptance-crash experiment | PASS reviewed local scope |

## Phase 5 acceptance additions

Source: actual owner message prompts/007-phase5-authorization.md plus baseline original PDF/master prompt.
Detailed implementation contract: phase5-design.md. Individual local evidence does not yet declare the phase gate complete.

| ID | Requirement/component | Acceptance criterion | Verification | Status |
|---|---|---|---|---|
| P5-01 | Real starting point/Git | Clean audited v0.4 HEAD, exact requested branch, prior refs retained | git fetch/status/branch/PR discovery in development-log | PASS |
| P5-02 | Additive persistence | 0004 data unchanged, no automatic publication/cadence reconstruction | 0004 fixture -> 0005 exact row comparison + metadata check | PASS local |
| P5-03 | Explicit publication | Disabled page/empty publications by default, separate public labels, history extra opt-in | DB CRUD, browser UI selection | PASS local |
| P5-04 | Management consistency | Version conflicts preserve drafts and monitor config/incidents unaffected | Parallel 200/409, publication draft component test, browser monitor version=1 | PASS local |
| P5-05 | Separate public entrypoint | No management routes/docs/OpenAPI or mutations through public ASGI/nginx | Complete route/method privacy tests + public Docker asset inventory | PASS local |
| P5-06 | Safe projection | No private URL/name/ID/group/recipient/body/errors/leases/outbox fields | Exact DTO keys + sentinel REST/SSE assertions | PASS local |
| P5-07 | Public realtime | Two independent clients reflect real worker DOWN/UP without reload | public.spec.ts real browser | PASS initial browser |
| P5-08 | Reconnect/revocation | Fresh snapshot after reconnect, remove hidden service/page/history permission | DB generator + browser + late REST component regression | PASS local |
| P5-09 | 24h/7d/30d analytics | Successful observed / observed, null at zero; no synthetic healthy metrics | PostgreSQL aggregate and component tests | PASS local |
| P5-10 | Honest gaps | Interval-capped coverage, legacy NULL cadence, no failure backfill | Bounds/config/legacy/gap tests and 0005 fixture | PASS local |
| P5-11 | Bounded PostgreSQL work | One indexed SQL aggregate and bounded bucket payload | Dense 10000-row fixture, one query / 360 buckets | PASS local fixture; fleet performance later |
| P5-12 | Charts/accessibility | Real bucket means, explicit NO DATA, accessible aggregate table | Component zero-vs-null test + browser chart/mobile assertions | PASS local |
| P5-13 | Local failures | Loading/errors/retry; no stale public restoration after unavailable/disconnect | PublicApp/AnalyticsPanel component tests | PASS local |
| P5-14 | No Phase4 policy rewrite | Carry queued DOWN issue to final acceptance review | ACC-EMAIL-01; notifications/dispatcher diff remains empty | PASS recorded; acceptance risk OPEN |
| P5-15 | Full regression | All prior backend/component/browser and live smoke/fault scenarios retained | 121 backend, 26 component, 7 browser, phase1/2/3/proxy/4 real reruns | PASS local |
| P5-16 | Hosted CI | Python + UI + actual Compose browser job successful on published implementation | Run 39390308186 on exact 9c155c3: 121 backend/26 component/7 browser, three jobs SUCCESS | PASS hosted |
| P5-17 | Review/docs/checkpoint | Privacy/races/query review, README/progress/evidence, real commits, stop before Phase6 | review.md, phase5-checkpoint.md, actual log/commits; ACC-EMAIL-01 retained | PASS phase5 scope; owner review next |

## Phase gates and effort estimates (planning ranges)

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

## Phase6 current evidence amendments (not full phase completion)

Historical phase-specific additions above describe their delivered checkpoints. Current baseline
corrections: GEN-10/GRP-04 and FND-02 now include actual SMTP/outbox/maintenance/public schema;
UI-09 includes real charts. These earlier "later" labels must not be read as current absence.
SCN-03/04 and NTF-02/03 now include the stronger new-incident delayed-dispatcher policy in0006;
unknown legacy eligibility is not inferred. SCN-13 has a real mixed50x30 five-minute proof with
475 persisted observations, actual per-monitor non-overlap and slow/fast cadence. This is not the
still-pending50-monitor fault matrix. HIS-09/SCN-15 now have repeated synthetic fleet/month
measurements: warm p95<1s up to100k single-monitor rows, but first1.143s exceeds target;
status remains PARTIAL for unconditional first-query latency. See phase6-performance.md.

| ID | Owner/engineering criterion | Acceptance / executable verification | Current status |
| --- | --- | --- | --- |
| P6-REQ-01 | Audit with source provenance | Original PDF re-extracted; per-finding repro/cause/severity/fix/evidence in phase6-audit.md | PARTIAL full final audit; ten confirmed findings recorded |
| P6-REQ-02 | Correct ACC-EMAIL-01 | Required DOWN then RECOVERY across dispatcher delay/retry/restart; no maintenance-only stale pair | PASS new-incident PostgreSQL + real phase6-email-smoke; legacy unknown boundary explicit |
| P6-REQ-03 | Aggregate public health | Ten-case active/paused/fresh/stale/no-data table, exact privacy fields retained | PASS actual PostgreSQL tests |
| P6-REQ-04 | Analytics edges | Manual bursts/same timestamps/legacy/exact end/coverage union | PASS new PostgreSQL regression; existing SQL preserved |
| P6-REQ-05 | Expired preflight safety | Claim expired before HTTP never invokes checker; valid lease refreshed | PASS new regression + actual prior32s smoke |
| P6-REQ-06 | Sustained real50x30 + resources | Five-minute isolated worker/HTTP/DB, events, CPU/RAM, latency/browser | PASS measured steady experiment; complete boundary planned/missed counters PARTIAL |
| P6-REQ-07 | Dense monthly benchmark | Synthetic10k/100k/500k/1m fleet,100k one-service, first/warm percentiles/plans/sizes | PASS experiment; first-query budget PARTIAL |
| P6-REQ-08 | Faults under50-monitor load | Stop/restart worker/backend/DB/simulator, manual/edit/pause/SSE cases | NOT VERIFIED as a50-monitor matrix; small-fleet current fault suites PASS |
| P6-REQ-09 | Security acceptance | SSRF/privacy/Host/dependencies/history and production boundaries | PARTIAL independent review + regression; full final security gate pending |
| P6-REQ-10 | Monochrome all-screen redesign | Unified tokens, all functional sections, dialogs/filters/diagnostics/public UI | TODO; baseline mobile overflow fix is not redesign |
| P6-REQ-11 | Responsive/keyboard/a11y/visual | Four strict viewports, keyboard journey, automatic checks, actual screenshots | PARTIAL four-width50-row baseline proof; complete accessibility/design NOT VERIFIED |
| P6-REQ-12 | Full exact-commit CI/docs/review | Local gates, final acceptance review, private completed-stage push then actual CI | PARTIAL local first-increment gates; Phase6 not uploaded/hosted/complete |

Do not combine these additional owner/engineering criteria with the133 baseline as literal employer
PDF wording. No full-product readiness percentage, exactly-once SMTP or unlimited-scale claim.


## 2026-10-20T15:56:02+05:00 — v0.6 continuation evidence

This dated amendment supersedes earlier partial current-status wording; historical phase evidence remains.

| IDs | Disposition | Evidence / limits |
|---|---|---|
| UI-01..13; P6-REQ-10 | PASS delivered UI scope |Admin/public monochrome; real controls;32components/11browser, four widths.12axe scans0violations; not complete WCAG certification |
| UI-07; P6-005..008 findings | PASS honest selection/deadline/navigation/coverage |Paused/UNKNOWN retained, maximum500 disclosed; no unlimited-list claim |
| P6-REQ-01/02/03/04/05/09 | PASS defined audit/local-security scope |149PostgreSQL tests/migrations; independent follow-up; real SMTP/Host/privacy/dependency review |
| P6-REQ-06/08; SCN-12..14/17/18 | PASS measured steady+fault scope |Original300s retained; new50-monitor faults206s,295HTTPends,0loggedoverlaps,290persisted at shutdown matched to actualHTTP. No theoretical fixed-rate missed count claimed |
| P6-REQ-07; HIS-09; SCN-15 | PASS bounded measurement; universal<1s LIMITED |100000single-monitor rows;3cold/21warm;1aggregateSELECT+1localsetting; coldmax635ms/warmp95867ms/warmp99max1180ms. Synthetic/sharedhost/OS-cache limits |
| P6-REQ-11/12 | Responsive/a11y/local checkpoint PASS; hosted CI requires exact-SHA outcome |phase6-final-checkpoint.md/log; no remote PR/merge falsely claimed |

GEN-07 exact model identifier, owner's essay and final employer access/submission remain owner inputs. This is a phase checkpoint, not final submission acceptance.
