# Phase6 notification obligation (0006)

This explicitly supersedes the quick-recovery cancellation rule in phase4-design.md for
new DOWN deliveries. The original PDF asks for DOWN then RECOVERY; dispatcher latency must
not erase a confirmed, permitted incident. SMTP acceptance and database commits remain separate.

## Persisted policy

`down_eligible_at` records the earliest unsuppressed instant for the frozen email's routes.
For each still-configured route, union monitor windows and that group's windows, including
touching/overlapping scheduled windows. The earliest uncovered instant across routes wins.
`down_required` records an earned obligation, independently of SMTP attempts or rejection.
At confirmation outside maintenance it is true immediately. During maintenance the deadline
survives dispatcher downtime. Recovery compares the stored deadline with its HTTP-completion
timestamp, rather than processing time; exact recovery at window end alone does not prove a
post-maintenance outage. A prior possibly accepted attempt still requires ordered reconciliation.

Maintenance and group mutations lock group parents then monitor UUIDs in order. Before changing
policy they retain earned deadlines, then recompute future eligibility under the new configuration.
This prevents retroactively extending maintenance from erasing an already-required alert.
Removing the final frozen/current route terminally cancels its pending DOWN even if dispatcher
is stopped; re-adding recipients applies to future incidents. One remaining permitted shared
route keeps the same address delivery. New recipients never receive old incidents.

| Condition | DOWN | RECOVERY |
| --- | --- | --- |
| Confirmed outside applicable maintenance, recovery before dispatcher | Retain; send when currently allowed | Wait for same-address DOWN SENT |
| Entire incident within applicable windows, no uncertain attempt | Cancel stale DOWN | Cancel stale RECOVERY |
| Window ends while incident remains open, dispatcher offline | Deadline earns obligation | Later recovery retains ordered pair |
| Window extended before old deadline | Recompute future deadline | Suppress if recovered before eligibility |
| Window extended after a gap outside maintenance | Retain earned deadline; suppress actual attempt while maintained | Wait for DOWN then current maintenance end |
| Successful HTTP observed inside window, persisted after deadline | Re-evaluate obligation at observation timestamp | No stale pair unless prior attempt may have been accepted |
| DOWN already SENT, recovery during maintenance | Keep SENT | Defer until a route allows sending |
| All frozen routes revoked | Terminal cancellation; no resurrection on re-add | Cancel if DOWN cancelled |
| Incident closed PAUSED / CONFIG_CHANGED | Cancel pending DOWN on preflight | No recovery event |
| Definite SMTP refusal, then recovery outside maintenance | Keep required DOWN and persisted retry identity | Wait for DOWN acceptance |
| Ambiguous acceptance/process crash | Retry existing delivery; possible physical duplicate | Wait for known DOWN acceptance |
| Permanent refusal / eight failed attempts | FAILED; operator investigation needed | Cancel; no false recovery |

## Upgrade boundary

0006 only adds nullable eligibility and false obligation fields. It does not rewrite published
0001–0005 or resurrect SENT/CANCELLED/FAILED rows. Legacy deliveries retain their prior policy
when eligibility is unknown: reconstructing historical recipient/maintenance intent would be
guesswork. Newly confirmed incidents use the new policy. Existing unknown historical mail must
be reviewed explicitly by an operator, rather than mass-mailed during upgrade.

## Evidence

`phase6-reproduction.xml`: before fixes, four failures (email, expired lease and two paused cases).
`test_phase6_policy.py`: deadline/edit/delete/offline/retry/shared-address/revocation and delayed
recovery persistence regressions; actual PostgreSQL with controlled HTTP/clock, not real SMTP.
`scripts/phase6_email_smoke.py`: real HTTP worker, separate dispatcher, Mailpit, backend/worker/
dispatcher restart and SMTP refusal followed by recovery. Reports persist IDs/order/attempts.
Existing `phase4_fault_smoke.py` retains maintenance suppression and acceptance-crash scenarios.
No exactly-once physical delivery or unbounded retry/mailbox-delivery guarantee is claimed.
