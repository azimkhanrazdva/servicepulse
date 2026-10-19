# ServicePulse working agreement

Read docs/requirements.md, docs/architecture.md and docs/progress.md before changing code.
Implement in verified increments: inspect, implement, test, review, document, commit.
Keep backend, frontend and worker separate. PostgreSQL is the source of truth.
Never invent test outcomes, dates, commits, metrics or completed requirements.
Record actual commands and outcomes in docs/development-log.md; refresh progress.md.
Use feature branches and Conventional Commits. Do not backdate or rewrite history.
Ask the owner before public PR, merge, public publication, architectural replacement,
destructive data changes or actions involving real credentials. Local test credentials are disposable.
Owner authorized GitHub uploads after each completed and verified stage on 2026-10-19.
Repository must remain private: https://github.com/azimkhanrazdva/servicepulse.
Push real local commits after verification; unfinished stage changes stay local. Never force-push.
This authorization does not grant automatic PR creation, merge or a change to public visibility.
No secrets in Git. No arbitrary private HTTP targets; test exceptions must be explicit and narrow.
Preserve observation gaps; do not turn missing checks into failed checks.
No decorative controls or fabricated monitoring data. Label unfinished features honestly.
Run relevant tests, lint, typecheck and build. A NOT VERIFIED item is never PASS.
Do not begin the next phase while critical checks in the current phase fail.
Each requested stage ends at a verified checkpoint for owner review.
