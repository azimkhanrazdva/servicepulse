# Phase6 measured performance — local scope and remaining gates

These are real experiments, not universal guarantees. Windows host, Docker Linux/x86_64,
16 reported CPUs,8170147840 bytes memory, Python3.12.15, PostgreSQL17.11, Node24.15.0.
Other local Compose/build/browser regression activity shared the host; projects/databases were
isolated, CPU/RAM were not exclusively reserved. Timestamps and raw events remain in artifacts.

## Real mixed50-monitor HTTP load

`python scripts/phase6_load.py --seconds 300` uses compose.performance.yaml and its own volume;
it never resets the user's database. Real worker scheduler/checker with a measurement wrapper,
PostgreSQL persistence, HTTP simulator and nginx/React. Every interval is30s; fixed delay starts
the next schedule after persistence completes, rather than promising one launch each wall-clock30s.

Mix:25x100ms200;10x800ms201 expected201;5x32s200 with40s timeout;5x100ms500 expected200;
5x6s targets with2s timeout. These are real HTTP observations, unlike the separate synthetic history.

Latest complete run:2026-10-20T04:22:18.336179Z observation start,300.0 measured seconds.

| Metric | Actual |
| --- | --- |
| Started / HTTP finished / persisted results | 475 /475 /475 |
| Successful / failed / cancelled / unpersisted-at-shutdown | 375 /100 /0 /0 |
| Fast monitor count | 10 each, all25 |
|32s monitor count | 5 each, all5 |
| Maximum / mean measured HTTP concurrency | 41 /3.42446 |
| Same-monitor overlapping measured HTTP calls | 0 |
| HTTP elapsed p50 /p95 /p99 /max | 0.15405 /32.01172 /32.06605 /32.06986s |
| Steady scheduler delay p50 /p95 /p99 /max | 0.25622 /0.55249 /0.59704 /0.60277s |
| All-launch delay p95 /max | 4.84961 /4.99771s, includes fixture setup while worker stopped |
| API overview p50 /p95 /max,43 samples | 16.55 /35.16 /66.49ms |
| Dashboard HTTP p50 /p95 /max,43 samples | 4.07 /27.60 /41.23ms; HTML response, not full render |

Actual all50 browser rendering was also measured on the first run at four viewport sizes;
post-correction measurements~240–295ms include navigation until the50th row appears. This is a
four-page sample, not a browser p95 or interaction latency guarantee. Evidence/load experiment
includes the older baseline theme, not the unfinished monochrome redesign.

Resource samples every~7s (docker stats adds overhead),43 samples/service. Docker CPU100% means
roughly one logical CPU, not all16 host CPUs. Container MemUsage is not process RSS or continuous peak.

| Service | CPU mean /sampled max | Container memory sampled max |
| --- | --- | --- |
| Backend | 11.23% /16.82% | 72.41MiB |
| Worker | 4.33% /39.61% | 67.37MiB |
| PostgreSQL | 6.38% /35.97% | 72.14MiB |

First run actually lasted301.875s and also persisted475 results, max concurrency40. Its collector
looked up container IDs before starting worker and accidentally omitted worker resource samples.
Corrected with compose ps --all, preserved first raw reports, then actually repeated the five minutes.
Latest resources include all three services; no omitted worker metric is invented for the first run.
The raw PostgreSQL stats snapshot was captured during the first run and is explicitly a separate
snapshot, not a second-run total. Transaction rollback counts include routine read-session rollbacks.

Sources: phase6-load.json/events.jsonl/analysis.json; phase6-load-first.json/events-first.jsonl/
analysis-first.json; phase6-load-db-snapshot.json; phase6-load-browser.json.

No fixed-rate500-launch target is imposed. The report records due_at for each actual launch and
cadence/delay. No dropped schedule sequence was observed, but future/not-yet-started boundary
schedules are not independently counted; planned/missed end-boundary accounting remains narrower
than the complete owner metric wish list. Absolute non-overlap under process suspension beyond a
lease is not claimed. Worker/DB/simulator interruptions while all50 run remain a separate gate;
current genuine fault/restart evidence uses smaller isolated scenarios plus the real32s/30s pair.

## Synthetic PostgreSQL monthly benchmark

Own project `servicepulse-phase6-benchmark`, disposable servicepulse_test DB. Fresh model migrations;
no worker/simulator needed. Generated rows are synthetic and never presented as HTTP observations.
First dataset uses50 paused fixture monitors. Each size replaces only this isolated history; later
DELETEs leave table/index bloat, deliberately reported by actual pg_table_size/pg_indexes_size.

Eight runs/dataset: first call reported separately; seven subsequent timings use nearest-rank
p50/p95/p99. With seven samples p95/p99 both equal the maximum. No OS/PostgreSQL cache purge:
"first" is not a proven cold-disk measurement. Every response360 buckets and~55–60KB JSON.
Timing includes aggregate/session/Python bounded transformation, excludes HTTP transport. Separate
EXPLAIN(ANALYZE,BUFFERS,FORMAT JSON) is saved; its instrumented timing is not mixed into percentiles.

| Table rows | Queried monitor rows | First ms | Warm p50 ms | Warm p95/p99/max ms | Table/index bytes |
| --- | --- | --- | --- | --- | --- |
|10000 across50 |200 |12.45 |7.16 |7.80 |1048576 /925696 |
|100000 across50 |2000 |19.00 |16.97 |17.55 |11165696 /11960320 |
|500000 across50 |10000 |65.65 |59.11 |63.93 |61743104 /61743104 |
|1000000 across50 |20000 |254.02 |173.00 |178.81 |162906112 /145244160 |
|100000 on one monitor |100000 |1142.96 |524.61 |608.97 |173031424 /154345472 |

Do not describe1m total as1m queried for one service. The dense100k single-service scenario exceeds
the zero-overhead86400 observations/month at30s. Largest table distribution and per-monitor density
are different stress dimensions. Zero-overhead50x30 monthly ceiling is4320000 observations;
fixed delay plus real HTTP/persistence lowers it. The measured475/300 rate, extrapolated only as an
illustration, is4104000/month; not a month-long observed production result.

Warm p95 is under the project's1s target in these runs. Dense first call1.143s exceeds it; all-eight
nearest-rank p95 therefore also1.143s. Query-plan review found sequential scan of100k matching rows
and external-merge sorts/temporary blocks (instrumented execution1043.233ms). This is a measured
remaining first-call/large-density risk, not hidden behind warm numbers. No speculative Redis/index/
work_mem change was applied. Repeat dedicated first/warm trials and optimize only the measured sort/
materialization bottleneck before claiming unconditional monthly latency.1m per single monitor and
the whole theoretical4.32m fleet are not measured here.

Command sequence (only named disposable project may be removed):

```powershell
docker compose -p servicepulse-phase6-benchmark -f compose.performance.yaml up -d --build db migrate
docker compose -p servicepulse-phase6-benchmark -f compose.performance.yaml run --rm --build --no-deps -e PERFORMANCE_BENCHMARK=isolated-synthetic-history -v "${PWD}/artifacts:/evidence" backend python tests/benchmark_history.py
docker compose -p servicepulse-phase6-benchmark -f compose.performance.yaml down -v --remove-orphans
```

Raw source: artifacts/phase6-history-benchmark.json. Benchmark PASS means completed correctly with
verified counts/buckets/plans; it is not a universal <1s performance acceptance PASS.


## 2026-10-20T15:53:12+05:00 — Additional fault and cold/warm experiments

No repeat of the steady300s load was performed in this continuation. New unique test projects retain volumes; cleanup uses `down --remove-orphans` without `-v`. Main owner volumes were not reset.

`python scripts/phase6_fault_load.py`:206.172s end-to-end including startup/configuration;50 monitors,30s interval,47 fast200 + one32s200 + one500 + one8s/2s timeout. Worker, database, backend and simulator restarts; edit/run/pause/resume/delete/replacement/group changes; two real Chromium clients with OPEN/CLOSED incident assertions and a fresh post-reconnect snapshot. Six scenario groups PASS. Worker recovery16.547s; PostgreSQL recovery22.360s (includes waiting for actual next observation).

Logged HTTP starts295/ends295:266 success,7 unexpected status,13 timeout,9 network errors caused by the scenario. Maximum concurrency17; same-monitor overlaps0; scheduler delay p50 .319s/p95 1.740s/p99 7.162s/max8.560s including faults and manual scheduling. This is not a fixed-rate missed-count denominator. API overview20 samples p50 9.826ms/p95 24.752ms/p99 25.762ms. One resource snapshot, not percentiles: backend12.48%CPU/62.79MiB; DB5.55%/54.25MiB; worker1.98%/63.25MiB. Final live snapshot289 results; after shutdown persistence audit290 (one in-flight completion). Each persisted timestamp matches a real logged HTTP completion within1s, duplicate timestamp groups0, incidents only on intentionally failed monitors. No synthetic gap results or false fleet incident found. Raw counter values are in phase6-fault-load.json; PostgreSQL xact_rollback includes normal session rollback and is not an application-error count.

First fault run failed because the harness checked simulator recovery before HTTP readiness; phase6-fault-load-first.json retained. A second earlier background attempt was host-interrupted (exit1073807364), not counted PASS. Final UUID project f82127 passed after harness corrections. Browser and log/persistence evidence are separate files.

Dense synthetic fixture:100000 results for one paused monitor over~28.9days,360 month buckets,~55.4KB JSON. `python scripts/phase6_cold_history.py` restarts PostgreSQL three times; shared_buffers cold, OS cache retained. Three fresh-process first calls and21 warm calls. Before fix cold p50 1.101s/max1.327s; warm p50 1.009s/p95 1.599s/p99 1.694s. Host also ran builds/browser tests: CPU was not reserved.

Retained original EXPLAIN identifies468.637ms JIT compilation as a major additional cost, alongside external sorts. Minimal transaction-local JIT fix keeps SQL/indices/semantics. After fix cold p50 .554s/p95/max .635s (only3 samples); warm p50 .532s/p95 .867s/p99/max1.180s (21 samples). All counts asserted100000/360; total statements2 =1 setting +1 aggregation SELECT. Timings include connection/session/bounded Python transformation, exclude HTTP; serialization1–3ms is separately measured. `phase6-history-plan-no-jit.json` records instrumented589.301ms, no JIT section; temp sorts remain. Do not call three samples a production p95 or promise every call under1s.

The first new cold harness fixture placed earliest data exactly30days ago; later trials correctly failed the100000-count assertion as samples aged out. Retained failure evidence; fixture now starts29days ago and remains within the month for the experiment. No assertion was weakened. Before/after successful raw reports are retained separately. New files: phase6-cold-history-first-failure.json, phase6-cold-history-before-jit-fix.json, phase6-cold-history.json.
