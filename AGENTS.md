# ServicePulse working agreement

Read docs/requirements.md, docs/architecture.md and docs/progress.md before changing code.
Implement in verified increments: inspect, implement, test, review, document, commit.
Keep backend, frontend and worker separate. PostgreSQL is the source of truth.
Never invent test outcomes, dates, commits, metrics or completed requirements.
Record actual commands and outcomes in docs/development-log.md; refresh progress.md.
Use feature branches and Conventional Commits. Do not backdate or rewrite history.
Ask the owner before remote push, public PR, merge, publication, architectural replacement,
destructive data changes or actions involving real credentials. Local test credentials are disposable.
No secrets in Git. No arbitrary private HTTP targets; test exceptions must be explicit and narrow.
Preserve observation gaps; do not turn missing checks into failed checks.
No decorative controls or fabricated monitoring data. Label unfinished features honestly.
Run relevant tests, lint, typecheck and build. A NOT VERIFIED item is never PASS.
Do not begin the next phase while critical checks in the current phase fail.
The first delivery ends at a verified vertical slice for owner review.
