# Open issues for the final acceptance audit

## ACC-EMAIL-01 — confirmed outage may produce no mail before quick recovery

Origin: Phase4 audit, explicitly carried forward by the owner at Phase5 authorization.
Priority: HIGH acceptance risk for the strict employer interpretation; existing behavior is documented.

Employer task3 expects a DOWN email followed by recovery, without repeated emails during one incident.
Current Phase4 policy cancels a queued DOWN when no SMTP attempt was authorized and the incident
has already recovered, even outside maintenance. A slow/offline dispatcher can therefore miss both
emails for a confirmed real outage while the incident remains persisted. Existing test:
test_recovered_before_down_send_cancels_both. This is distinct from suppressed maintenance-only outages.

Phase5 deliberately does not change notification routing, cancellation or retry policy. Before final
submission, decide and verify a separate policy correction (preserve outside-maintenance historical
DOWN/RECOVERY ordering while suppressing maintenance-only stale pairs), or explicitly obtain owner
acceptance of the narrower behavior. Do not label the stronger guarantee satisfied without evidence.
This issue does not block implementing isolated public pages/analytics; it remains open for final acceptance.
