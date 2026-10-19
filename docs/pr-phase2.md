# feat: add versioned monitor management and groups

Prepared PR description; no remote PR is created automatically. Base: main (bd43629).
Head: feat/monitor-management-groups, descended from the real first-slice checkpoint.

Monitor settings previously could not be edited or paused, and clients could not organize
checks into groups. This change adds working management UI/API, persistent groups and recipients,
and version conflicts that preserve a losing client's draft rather than silently overwrite it.

## Behavior and implementation

- Additive Alembic 0002 keeps old monitors/results, adding config versions/manual request flag,
  groups, normalized membership and recipient tables with cascading foreign keys/indexes.
- PUT settings and pause/resume compare captured config_version under row lock; stale requests
  return 409. Browser deletions include a version and native confirmation.
- Active lease remains through changes. Worker checks config/state before I/O and persistence,
  discards obsolete results, keeps pending manual requests due, and recovers leases after restart.
- Every settings edit resets current state/metrics; historic observations retain their version.
- Group config/membership/recipients are atomic. Aggregate state ignores PAUSED, then
  DOWN > UNKNOWN > UP; all paused PAUSED; empty UNKNOWN.
- Existing default SSE monitor payload remains compatible; named groups events share a
  REPEATABLE READ snapshot. UI preserves original style and receives changes across clients.
- Email-validator is used through Pydantic for recipient syntax. Email dispatch remains phase 4.
- ESLint added to frontend checks and CI; migration harness verifies a real legacy fixture upgrade.

## Executed verification

- Full backend suite including prior tests, CRUD, versions, DB constraints, group settings,
  active edit/pause/resume/delete races, competing edits/claims and late manual queue.
- Frontend unit tests cover existing paths plus edited payload/version, conflict draft retention,
  explicit reload, validation messages, group recipients and delete confirmation.
- Real browser tests retain first slice/reconnect/mobile and add two-client management/groups.
- Real simulator smoke waits over 30s while paused and restarts backend/worker during changed
  configuration; proves retained settings/recipients and no stale/synthetic failed observations.
- Commands, actual counts/timestamps and machine reports: development-log.md and artifacts/.
  Hosted CI status must be read from its actual run, never inferred from workflow existence.
  Actual phase2 run: https://github.com/azimkhanrazdva/servicepulse/actions/runs/39319384324,
  success on implementation 034b4bda783e0a69a47d4c4875ea05fc36819e19.

## Remaining scope

Persisted incidents, transactional email outbox/retries, maintenance, public privacy page,
uptime/charts, sustained 50-monitor performance and monthly history benchmark remain pending.
Trusted local management only. No load/exactly-once SMTP/complete-product claim.

## Review links

- [Development log](development-log.md)
- [Architecture](architecture.md)
- [Requirements and evidence](requirements.md)
- [Provenance audit](requirements-provenance.md)
- [GitHub publication policy](github-workflow.md)
