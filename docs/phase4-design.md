# Phase 4 notification contract

The original FastAPI/PostgreSQL/worker/SSE architecture remains. A separate dispatcher process uses
the standard-library SMTP client through a bounded thread task; no broker or new runtime dependency.
Migration 0004 adds maintenance_windows, notification_events, notification_routes and notification_deliveries.
Existing incidents get notifications_enabled=false; no historical events or upgrade mailing. Newly
confirmed incidents explicitly opt in. Event/routes/deliveries join the existing monitor-locked transaction.

## Routing and recipient policy

- Event unique (incident_id,event_type), DOWN/RECOVERY only. Incident UUID is stable.
- Freeze group routing and recipient addresses at confirmation, even while maintenance suppresses sending.
  Recovery inherits those frozen routes. New groups/recipients apply to future incidents only.
- Normalize addresses case-insensitively for delivery deduplication; this deliberately treats local-part
  case variants as one operational address. Each event/email has one delivery across all group routes.
- Before each attempt require current membership and recipient presence. Removing all frozen routes
  permanently cancels a pending delivery; re-adding later does not resurrect it. Removed groups revoke
  their routes; monitor deletion cascades events/deliveries. No newly configured address receives old mail.
- Route group UUID intentionally has no FK: retains historical snapshot and avoids group->monitor versus
  worker monitor->group FK lock inversion. Eligibility joins live membership/recipient rows, so deleted
  groups cannot authorize delivery. All other event/delivery/window relationships have cascading FKs.

## Maintenance and SMTP authorization boundary

UTC start_at <= now < end_at. Monitor windows suppress every route. Group windows suppress only that
group. A shared address can be notified through any eligible non-maintained group, once. Overlaps are
a union. Monitoring, state, observations and incidents continue unchanged. UI badge means one or more
routes are suppressed, never that DOWN is UP. A group badge denotes its own group window.

Every claim undergoes final database preflight and persisted send_started_at immediately before SMTP.
SMTP runs outside database transactions. Suppression is guaranteed at that authorization evaluation:
an attempt already authorized/in flight cannot be recalled if maintenance begins or settings change
concurrently afterward. Scheduled time boundaries likewise cannot revoke a DATA command already in
flight. New attempts always revalidate. This is an explicit synchronization limit, not a claim of atomic
email/maintenance ordering or a transaction held across network I/O.

## Ordering, failure and reconciliation

Queued DOWN with no authorized attempt is cancelled when recovered; corresponding RECOVERY is cancelled.
If an attempt was already authorized and acceptance is uncertain (process crash/disconnect/timeout),
retry that DOWN before RECOVERY, even if recovery has occurred. This may produce a duplicate/stale DOWN
but preserves order and eventual recovery for an address that may have received the first attempt.
Definitive SMTP rejection clears the authorization marker; a recovered incident then cancels the stale
DOWN instead. Administrative PAUSED/CONFIG_CHANGED never generates RECOVERY; pending old DOWN is cancelled
on preflight. Already authorized SMTP may finish. A known SENT DOWN is retained for diagnostics.

RECOVERY waits for the same address's DOWN status SENT. If recovery happens inside maintenance after
DOWN was accepted, RECOVERY remains pending until an applicable route is allowed. If DOWN was suppressed
throughout the outage, no stale pair is sent. Events created during suppression are persisted pending;
the two-second reconciliation tick releases eligible delivery independently of any new HTTP observation.

Claims use SKIP LOCKED plus UUID leases; stale tokens cannot acknowledge a newer claim. Attempts are
counted at actual authorization, not suppressed polls. Retry intervals: 5,10,20,40,80,160,300,300 seconds,
maximum 8 attempts. SMTP 4xx retry; 5xx permanent failure; bounded category-only errors avoid exposing
server details. Process cancellation retains lease. SMTP sockets have per-operation timeout; the lease
has a conservative margin. Arbitrary process suspension can still overlap physical network attempts.
Stable Message-ID is diagnostic, not a receiver deduplication guarantee. DATA success defines acceptance;
the socket is closed without allowing a failed QUIT to reclassify an accepted message as rejection.

Unique logical event/delivery creation is database-enforced. Persisted retry schedules provide at-least-once
attempts with bounded retry exhaustion; SMTP acceptance is not proof of mailbox delivery. A crash after
acceptance and before DB acknowledgment may duplicate a physical message. No absolute exactly-once claim.
No SMTP password/authentication/TLS configuration is exposed through API: this phase supports the local
Mailpit catcher only. [Mailpit API documentation](https://mailpit.axllent.org/docs/api-v1/) supports the
actual-message verification; messages are sent over SMTP, not injected through the HTTP send endpoint.
