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
