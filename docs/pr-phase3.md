# feat: persist confirmed incidents and synchronize the incident journal

Prepared description only; no PR created. Base: feat/monitor-management-groups. Head: feat/incident-lifecycle.

Previously DOWN existed only as current monitor state. This change persists a single confirmed incident
at the failure threshold, retains it through repeated failures/restarts and closes it on actual recovery.
Pause and settings changes close administratively without pretending the site recovered.

- Additive 0003 migration preserves existing data without inferred incident history; database unique
  open-monitor index, closure/timestamp constraints and journal query indexes.
- Worker state, streak, observation and incident share one transaction behind the existing monitor lock
  and token/version fences. API pause/edit use the same lock order; delete retains cascade policy.
- Bounded joined REST journal with monitor/state/time filters, stable sort tie-break and pagination.
- Compatible named SSE snapshot/invalidation, live React journal, ticking durations and reconnect.
- Verified migration fixtures, 75 DB/backend tests, 11 component tests, 4 real browser tests and
  live simulator restart/cancellation/32s-request smoke. See phase3-checkpoint.md for exact evidence.

No email, maintenance, public page or sustained 50-monitor benchmark claim.

## Owner-authorized creation steps (do not execute without permission)

First create/review phase2 against main using the existing docs/pr-phase2.md:

```sh
gh pr create --repo azimkhanrazdva/servicepulse --base main --head feat/monitor-management-groups --title "feat: add versioned monitor management and groups" --body-file docs/pr-phase2.md
```

Then, if phase2 is still unmerged, create a stacked phase3 PR:

```sh
gh pr create --repo azimkhanrazdva/servicepulse --base feat/monitor-management-groups --head feat/incident-lifecycle --title "feat: persist confirmed incidents and synchronize the incident journal" --body-file docs/pr-phase3.md
```

Merge phase2 first only after owner review/authorization. Use a merge strategy preserving ancestry;
then retarget phase3 to main and review its remaining incident-only diff before an independently
authorized merge. Do not delete the phase2 branch while phase3 still targets it. If phase2 was squash
merged, reassess the diff with the owner before changing ancestry; never force-push or rewrite history.
