# ServicePulse — demo script (5–10 minutes)

Use a trusted local machine. All targets are the Compose simulator and all email goes to Mailpit. No employer or external provider email. Configuration changes below create a dedicated demo monitor/group/page; preserve existing owner data. Native date inputs use your local timezone; persistence uses UTC.

## Preparation (outside demo timer)

Prerequisites: Docker/Desktop Linux containers, Compose2.24.4+ (the isolated harness uses !override), Git; optional Python3.11+, Node24 and Chromium for automation. Copy .env.example to .env only when .env does not already exist. Keep the exact SIMULATOR_ORIGIN=http://simulator:8090 test exception; do not allow arbitrary private targets.

```powershell
docker compose up -d --build --wait
```

Dashboard localhost:8080; Mailpit localhost:8025; public ingress localhost:8081/status/<slug>; API docs localhost:8000/docs. Public root404 is intentional. Empty installations have no monitors/publications. `python scripts/seed.py` is optional configuration-only seed; no fake results. Browser automation below uses independent named fixtures instead.

## 0:00–2:00 — real monitoring and two clients

Open two separate browser windows/contexts on management8080. Add a monitor with unique name, URL http://simulator:8090/target/acceptance-demo, interval30s, timeout5s, expected status200, optional body ServicePulse ready, threshold2. Wait for actual UP/HTTP200, response time and last observation in both windows without reload. Open details:24h/7d/30d sample uptime, coverage, response graph and recent checks. A newly created service has low coverage, not a whole-month100% guarantee.

Create a group including this monitor and recipient demo@example.com. It is captured locally; Mailpit never forwards it. No demo control should change other monitors' target path. The following helper changes only acceptance-demo:

```powershell
python scripts/simulator_control.py acceptance-demo --status 500
```

For recovery use `python scripts/simulator_control.py acceptance-demo --status 200`. For timeout use `--delay 10` with a5s monitor timeout; restore with `--delay 0`. The helper uses stdin to avoid platform-specific nested JSON/shell quoting. It changes a named simulator target, never fabricates monitoring results; the worker still performs actual HTTP.

## 2:00–4:00 — confirmation, journal and SMTP

Run now once after500, wait for a new failed observation: state remains UP (one transient error). Run now again: DOWN, open incident and ticking duration in both clients. Mailpit has one DOWN. Run again while still500: same incident, no additional logical DOWN. Restore200 and run now: UP, recovered timestamp/closed duration and one RECOVERY. Notifications screen exposes real delivery IDs/status/attempts. Inspect mailbox subjects and recipient rather than assuming mail was sent.

## 4:00–6:00 — maintenance

Create an active monitor maintenance window (start before now, end ~one minute later). Set500, run two checks and observe DOWN plus MAINTENANCE badge: timestamps/checks continue; no mail. Either restore200 before the end (no stale maintenance-only pair), or leave DOWN and wait until end: dispatcher independently queues/sends required DOWN without a new result. Group windows apply only their group routes; overlapping windows remain suppressing until the last applicable window ends. Delete only this demo window when done.

## 6:00–8:00 — Public Status and privacy

Create a disabled page with unique slug acceptance-demo-<suffix>, add only the demo monitor with public label Demo service, explicitly enable page and aggregated history. Open its8081 link in two contexts. Observe live status, chart/gaps and publication labels. URL, internal monitor/group/recipient/window names, raw errors and delivery state are absent. Pause/resume admin monitor and observe public updates. Remove publication: both public clients remove the service without reload. Re-enable only if the owner wants to keep it public locally.

## 8:00–10:00 — persistence and evidence

Pause the demo monitor, note a saved result/incident ID, restart backend/worker/dispatcher with `docker compose restart backend worker dispatcher`, then verify settings/history/group membership remain. Resume and wait for another actual observation. There are no fake failed checks for restart time. No database volume is deleted. Remove only explicitly created demo resources if desired; preserve owner data.

## Automated equivalent

The implemented journey is stronger than a static demo and was actually executed against both the normal stack and a fresh committed clone:

```powershell
cd frontend
npx playwright test e2e/release.spec.ts --workers=1
cd ..
python scripts/phase7_clean_checkout.py --ref feat/final-acceptance-release
```

First command requires npm ci and npx playwright install chromium. The isolated command uses ports28000/28080/28081/28025, creates a unique DB volume and retains it after stopping its project. It does not remove volumes or reset owner data. Browser automation needs installed dependencies in the workspace. Evidence: phase7-release-journey.json and phase7-clean-checkout.json. Fault suites and300s/large-history experiments are separate, outside the5–10 minute presentation.


During the final engineering-evidence minute, open actual private PR#3 (with its dependent bases), the current branch Actions run and phase7-final-acceptance.md. Show the preserved475 steady/295 fault raw evidence and the warm1.180s outlier. Do not call prepared laterPR descriptions existingPRs or an empty-data uptime a measured SLA. No extra load run is needed during the demo.
