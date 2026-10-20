# Actual review PR

Created on the owner's subsequent request: https://github.com/azimkhanrazdva/servicepulse/pull/3
(base feat/incident-lifecycle, depends on #2). Prepared text below is historical.
No backdating or merge occurred.

# feat: add maintenance windows and durable email notifications

Prepared description only; no PR created. Base feat/incident-lifecycle, head feat/maintenance-email-outbox.

ServicePulse previously recorded incidents without alert delivery. This change sends real local SMTP
DOWN/RECOVERY alerts, suppresses applicable routes during scheduled maintenance and reconciles pending
work after windows end without waiting for another HTTP observation. Monitoring and real DOWN continue.

- Additive 0004 schema: maintenance, unique logical events, frozen group routes, per-address deliveries.
- Existing monitoring transaction atomically saves incident and notification work; SMTP runs separately.
- Deduplication across groups, recipient revocation, ordered recovery, durable retries/leases and diagnostics.
- Versioned maintenance CRUD, React timezone-aware editor, badges, filtering/pagination and two-client SSE.
- Upgrade preserves existing incidents/settings/history and explicitly disables historical mailing.
- 107 backend, 15 component tests, real browser/Mailpit/fault evidence in phase4-checkpoint.md.
- SMTP acceptance-before-ack crash demonstrates physical duplicates honestly: 3 messages/2 logical deliveries.

Limit: final authorization cannot recall an already in-flight SMTP command when a window/settings change
concurrently. No exactly-once or external mailbox delivery promise. Public pages/uptime are separate phases.

## Owner-authorized PR chain (prepared, not executed)

Phase2 targets main; Phase3 targets Phase2; Phase4 targets Phase3 until those bases merge.
Existing descriptions: pr-phase2.md and pr-phase3.md. Exact Phase4 creation command after authorization:

```sh
gh pr create --repo azimkhanrazdva/servicepulse --base feat/incident-lifecycle --head feat/maintenance-email-outbox --title "feat: add maintenance windows and durable email notifications" --body-file docs/pr-phase4.md
```

Merge in dependency order only after owner approval, preserving ancestry; then retarget each next PR
to main and review its remaining diff. Do not remove a branch while it is still a stacked base. If a base
was squash merged, reassess with the owner before altering ancestry; never force-push or rewrite history.
