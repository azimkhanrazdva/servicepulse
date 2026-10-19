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
