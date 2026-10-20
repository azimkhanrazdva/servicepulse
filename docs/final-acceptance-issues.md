# Open issues for the final acceptance audit

Phase6 update: ACC-EMAIL-01 has an explicit correction for newly confirmed incidents in0006,
documented in phase6-notification-policy.md and phase6-audit.md. The old account below is historical
evidence of the reproduced defect, not the current new-incident policy. New tests preserve the
outside-maintenance pair, suppress maintenance-only outages, retain retry IDs/order, and test
recipient revocation and delayed recovery persistence. Actual Mailpit/restart results are in
artifacts/phase6-email-smoke.json; acceptance-crash limits remain explicit.
Legacy deliveries with unknown historical eligibility are not silently replayed or inferred.
Final whole-product acceptance remains pending Phase6 redesign/security/accessibility/load-fault gates.

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


Phase6 continuation closure:149backend/32component/11browser,50-monitor faults, scoped security review and12axe scans0violations now pass. ACC-EMAIL-01 is corrected for new incidents; actual delayed/refused SMTP proof is artifacts/phase6-email-continuation.json. No unresolved confirmed HIGH in the tested local phase. Final employer submission/owner inputs still belong to Phase7; legacy eligibility and physical SMTP ambiguity remain explicit.
