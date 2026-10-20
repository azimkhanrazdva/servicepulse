# First checkpoint review

This is the implementation agent's separate code-review pass, **not an independent reviewer
or a completed final product audit**. Full incident/outbox/maintenance/restart/load/public
security review remains mandatory when those features exist.

## Resolved findings

| ID | Severity | Evidence / issue | Resolution / verification |
|---|---|---|---|
| REV-01 | HIGH | Initial Vitest 3 dependency tree: tinypool/mocker advisories | Updated Vitest 5.0.5, reran tests/build; artifacts/npm-audit.json reports zero findings |
| REV-02 | MEDIUM | Browser offline test retained Live for an existing SSE stream | Explicit offline close and online reconnect in App.tsx, regression unit and real two-context browser test |
| REV-03 | HIGH | Numeric-IP TLS pool key could allow reuse across virtual hostnames | Connection: close per request; original Host and IDNA SNI retained; checker tests assert header and SNI |
| REV-04 | MEDIUM | Slow initial REST response could overwrite newer SSE snapshot | Ignore initial list response after first snapshot |
| REV-05 | MEDIUM | Untrusted response charset could throw unexpected decoder exceptions | Match bounded raw response as UTF-8 with replacement; document policy |
| REV-06 | LOW | Empty CSS @import emitted build warning | Removed; build clean |
| REV-07 | LOW | Non-root container pytest could not write /app/.pytest_cache | Disable pytest cache in isolated container run |
| REV-08 | MEDIUM | Earlier test tables had no Alembic revision, breaking migration-aware reruns | Guarded disposable-test runner resets known test tables and revision metadata before migrations; repeated final image run passes 31 tests |

## Reviewed invariants

- Create validates unknown fields, name/URL length and numeric bounds; DB duplicates numeric bounds.
- Claims commit before HTTP; SKIP LOCKED prevents competing claim of one eligible row.
- Only free task capacity is claimed; worker uses a pooled, bounded async HTTPX client.
- Completion locks the row and checks claim UUID; deletion/lease replacement prevents stale writes.
- Completion and observation insertion share one DB transaction. No catch-up results are fabricated.
- DNS answers are checked before numeric-IP connection; redirects/environment proxy disabled;
  total timeout includes DNS and raw stream; compression is rejected and body cap is tested.
- API schema projection excludes lease tokens and DSN. There is no public projection yet;
  management API is explicitly private/trusted-local, not a public API.
- Native browser reconnect gets complete snapshots; independent browser contexts were tested.
- No fictional uptime, active-incident count, email-success indicator or unavailable navigation.
- Initial migration is explicit, not importing mutable ORM models. Separate test database refuses
  destructive setup unless both configured URLs end with /servicepulse_test.

## Remaining review items / limitations

- HIGH before public hosting: management has no auth/rate limiting; keep loopback binding and
  implement access boundary before internet exposure. No publication is authorized or claimed.
- HIGH for final submission: incident/outbox/maintenance/public requirements are unimplemented;
  first checkpoint must never be presented as assignment completion.
- MEDIUM: no live external HTTPS/SNI or egress firewall test; request construction alone is
  insufficient proof of TLS behavior across all DNS/CDN/network setups.
- MEDIUM: no actual stopped-process/restart/slow-check-over-interval test yet. A fenced lease
  prevents stale commits; absolute non-overlap during arbitrarily long process suspension
  beyond lease expiry is not guaranteed. Test and document the failure model in phase 3.
- MEDIUM: monthly history aggregation, coverage semantics and load measurements not done.
- LOW: SSE/database polling and list caps are appropriate for 50 monitors, not an unbounded fleet.
- LOW: Docker tags/build tooling and simulator transitive dependencies are not fully locked;
  application Python lock and npm lockfile cover the primary code paths.
- LOW: API logs are ordinary access logs; complete structured API errors/observability later.

These are visible checkpoint limits, not a release approval. No full security compliance or
exactly-once SMTP claim is made. See requirements.md for pending acceptance tests.

## Phase 2 review pass

This is another implementation-agent code review, not a claimed independent reviewer.
No fundamental architecture replacement was required.

- Monitor/group edits compare versions under row lock. Missing/invalid/stale versions produce
  explicit validation/conflict responses. Browser drafts are not silently replaced by SSE.
- Active lease stays in place through edit/pause/resume; worker checks both version/state
  before HTTP and before committing; deleted rows cannot be recreated by old tasks.
- Found and fixed a late completion overriding a queued immediate run after lease expiry;
  pending request now remains due, with a dedicated PostgreSQL regression test.
- Found and fixed a group post-commit reread race: concurrent delete could turn a successful
  mutation into 500. Responses are now assembled before commit while holding the group lock.
- Group updates lock group first and monitor IDs in sorted order; monitor config updates never
  acquire a group lock. Membership/recipient replacement is atomic, with FKs and cascade semantics.
- Monitor DELETE has optional config_version for old API clients. Browser always sends it;
  unversioned API deletion remains unconditional by design, not optimistic protection.
- Existing response/body/DNS/redirect guards remain. Email validation does not check actual
  deliverability or send messages; settings UI explicitly states delivery is future work.
- Default SSE monitor message preserved; named group snapshot uses the same DB transaction.
- New checks include 0001 legacy data upgrade, concurrent edits/mutations, a real >30s pause,
  actual backend/worker restart and browser two-client conflict/reload and group state updates.
- ESLint flagged the existing fake EventSource this-alias; fixed capture instead of suppressing.
  Prettier found two test files later; corrected and reran formatting successfully.

Remaining boundaries: no auth/public hosting approval, no incident/outbox/maintenance/public
projection, no sustained 50-monitor benchmark/month buckets, no full independent final audit.
Old HTTP work may finish after configuration change; it is discarded, not reclassified as an
observation under the new URL. All edits (including rename) conservatively reset live state.
Full arbitrary process-suspension non-overlap remains outside expiring-lease guarantees.

## Phase 3 critical review

Implementation-agent review of the final migration, lifecycle, API, React and tests. No separate
reviewer or independent-session claim. No BLOCKER/HIGH found within this phase's trusted-local scope.

- Atomicity: monitor row lock serializes worker completion with edit/pause/delete; incident insert,
  close, state, streak, result and lease commit together. Actual PostgreSQL division-by-zero test
  after lifecycle flush rolls changes back. A future outbox must join this same transaction.
- Uniqueness: partial unique monitor_id WHERE closed_at IS NULL is enforced by PostgreSQL;
  repeated/concurrent completions and old token returns cannot duplicate logical incidents.
  Direct invalid inserts test both uniqueness and administrative-vs-recovery constraints.
- Migration: no backfill or rewrite of settings/results; actual 0002 DOWN/group/recipient fixture
  stays unchanged. Fresh failure starts the tracked interval; missing earlier duration remains unknown.
- Recovery: only valid success sets recovered_at; PAUSED/CONFIG_CHANGED close with null recovery.
  Resume/reset policy and delete cascades remain consistent with v0.2, including rename resets.
- Concurrency: HTTP outside transactions, deadline shorter than lease; slow pair test demonstrates
  fast progress during 32s HTTP. Claim/expiry/cancel/restart tests retained, stale successes and
  failures tested. Arbitrary suspension beyond expiry and physical SMTP exactly-once are not claimed.
- API: bounded limits/offsets, validated UUID/state/order/timezones/ranges, one JOIN and no per-row
  query (150-row test). Name is current monitor name. Indexes cover time and monitor/time order.
- Realtime: additive named incidents event preserves original messages; filtered REST invalidation
  handles older incidents outside newest 50. Client cleanup prevents obsolete requests overwriting
  a new filter; reconnect and two contexts exercised in a real browser. Duration uses local clock.
- Security: no new target access path, redirect/private-target policy or proxy change. Simulator control
  stays internal. Management API/journal is private local data; public projection remains future work.

Deployment review subsequently found HIGH nginx DNS caching after backend container replacement:
direct API healthy but proxy 502, 3 browser tests failed. Fixed bounded Docker DNS refresh in proxy;
same-origin paths/headers/SSE settings preserved. A deterministic IP-replacement regression passed
with unchanged frontend container and final browser suite 4/4 passed. No unresolved HIGH remains.

Remaining priorities:
- MEDIUM: full-month aggregates/coverage charts and sustained 50-monitor experiment belong to later gates.
- MEDIUM: no authentication; trusted-local deployment only, unchanged. Public hosting needs its own review.
- LOW: offset pages can move during insertions; cap 10000 requires narrowing with time filters for deep history.
- LOW: each incidents SSE tick refreshes a bounded journal page; measure before replacing with revisions/keysets.
- LOW: wall-clock correction clamps negative incident duration; monotonic HTTP latency remains separate.
- LOW: container tags/action majors are not digest/current-major locked, as previously documented.

## Phase 4 separate critical review pass

This is an implementation-agent review pass from a critical-reader perspective, not a claim of an
independent model/reviewer. Code, actual SQL/SMTP faults and browser results underpin the conclusions.
No unexplained BLOCKER/HIGH remains in the requested trusted-local phase4 scope.

- Transaction boundary: lifecycle invokes event/routes/delivery creation before completion commit.
  Real SQL division-by-zero after flush rolls all of it back; original atomic-result tests remain.
- Routing: immutable confirmation snapshot, per-event/address uniqueness, current membership and
  recipient revocation. Shared addresses can use an eligible group without a suppressed group
  blocking an independent route. Group deletion cannot authorize mail; monitor deletion cascades work.
- Lock ordering: worker/dispatcher monitor before lifecycle/delivery; group edits group then monitors;
  route group UUID has no FK to avoid reverse FK locks. Maintenance replacement locks old/new parent
  groups then monitors (sorted UUIDs) before the child window; populated version read avoids stale ORM cache.
- Maintenance: database target XOR/time constraints, UTC half-open intervals, overlap union and real
  DOWN retained. Reconciliation acts without a new CheckResult and never invents observations.
- Send boundary: preflight/authorization transaction ends before SMTP. An in-flight send cannot be
  recalled by a concurrent new window, deletion, pause or recipient change; subsequent attempts
  recheck policy. A test pauses successfully while sender is blocked, proving no monitor transaction held.
- Delivery uncertainty: stable IDs and token fencing do not make SMTP exactly once. The actual isolated
  acceptance-before-ack crash produced a duplicate DOWN followed by RECOVERY, 3 physical/2 logical.
  Unattempted DOWN cancels on recovery; known rejection clears authorization; uncertain attempt drains
  before recovery. Permanent failure/exhaustion is terminal and requires operator investigation.
- Cancellation and restart: claimed leases persist; stale old owner cannot ack a new claim. Actual
  isolated dispatcher/worker restart and PostgreSQL outage retain IDs/config and create no fake results.
- SMTP error handling: bounded codes only, no raw server response or credential API. 4xx retry/5xx fail,
  timeout/disconnect ambiguous. DATA success is acceptance; failed QUIT cannot reclassify success.
- Resource limits: batches of five, socket timeouts, finite retry count, indexed claim query, bounded
  diagnostics and Docker dispatcher log rotation (10 MiB x 3). No SMTP network inside DB transaction.
- Frontend: actual API state, no fictitious controls; local timezone disclosed, UTC submitted. Exact
  select-label locator failed in browser and was corrected to observed combobox role. Tests retained.
  Review found a real LOW stale refresh error after reconnect; separate loading/mutation errors now
  clear only recovered fetch errors, preserving a 409 draft. Added component/browser regression.
- Security: local Mailpit, internal SMTP, loopback UI/API, no credentials in new source/config. Public
  projection remains absent, so no new public exposure of recipients, maintenance names or delivery state.

Remaining MEDIUM/LOW boundaries: no production SMTP/TLS/auth integration or rate limits; finite retry
exhaustion needs investigation and there is no manual retry UI; recipient local parts are case-normalized
by declared policy; SMTP batch time can extend the 2s loop cadence; arbitrary suspension can overlap
physical attempts; month/50-monitor/full security audit remain later phase gates. These are not hidden PASS claims.

## Later owner-requested Phase4 audit

See [phase4-audit.md](phase4-audit.md) for the original PDF mapping, exact attachment provenance,
PR #3/CI checks, current 109/15/5 test gate and rerun real SMTP/process faults (78.781s).
No confirmed BLOCKER/HIGH found within the trusted-local phase4 contract; product logic unchanged.
Audit added default-two-failure/outbox lifecycle and permanent-550 dispatch regressions, and explicit
first-failure assertions to the live harness. Queued-but-unattempted DOWN cancellation outside
maintenance is a material policy limit: no guarantee of mail for every historical outage after
dispatcher downtime. Other SMTP/exhaustion/public-deployment limits remain explicit in that report.
This remains an implementation-agent review, not an independent human/model approval.
