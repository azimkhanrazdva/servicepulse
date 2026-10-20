# Phase7 — проверка исходных измерений

Это повторный анализ сохранённых данных Phase6, а не новый нагрузочный прогон. Runtime scheduler/analytics не изменены. Скрипт `python scripts/phase7_acceptance_audit.py` заново разбирает реальные HTTP start/end и cold/warm samples; результат — `artifacts/phase7-performance-review.json`. Исходные отчёты сохранены с настоящими датами.

| Эксперимент | Проверенный результат | Граница вывода |
|---|---|---|
| 50 мониторов ×30s,300s steady |475 стартов/475 завершений/475 сохранённых результатов;375 успешных,100 ожидаемых ошибок; max concurrency41;0 пересечений одного monitor |Fixed delay: завершение +30s, не500 обещанных запусков по настенным часам |
| Scheduler steady |После исключения начальной подготовки p50 256ms/p95 552ms/p99 597ms/max603ms |`phase6-load-analysis.json`; смешанная cadence p50 30.552s/p95 32.570s/p99 62.470s:32s медленный ресурс закономерно запускается реже |
| HTTP steady |p50 154ms/p95 32.012s/p99 32.066s/max32.070s |Медленные и ошибочные ответы намеренные; это не API latency |
| 50 мониторов + worker/backend/DB/simulator faults |295 реальных start/end, max17,0 overlaps;266 success/7 unexpected_status/13 timeout/9 network_error |Шесть групп PASS206.172s вместе с подготовкой; нет выдуманного фиксированного количества «пропущенных» проверок |
| Fault scheduler/recovery |Delay p50 319ms/p95 1.740s/p99 7.162s/max8.560s; worker recovery16.547s/DB22.360s |Пауза сервера не создаёт результатов. После shutdown290 результатов против289 на живом snapshot: один реальный in-flight commit |
| API под fault load |p95 24.752ms |Контролируемый локальный опыт, не интернет SLA |
| Monthly dense history |100000 результатов одного monitor,360 buckets;3cold/21warm |Synthetic DB fixture, настоящие PostgreSQL SQL/driver/aggregation timings; не HTTP p95 |
| Cold |p50 554ms/p95=p99=max635ms |shared_buffers cold после restart PostgreSQL; OS cache retained; три образца |
| Warm |p50 532ms/p95 867ms/p99=max1.180s |Outlier выше1s сохранён; нет гарантии universal<1s |

Один вызов analytics выполняет SET LOCAL jit=off и один ограниченный aggregate SELECT. Это не загрузка месячных ORM строк в Python. EXPLAIN ANALYZE без JIT показывает589.301ms на100000 строк, временная сортировка остаётся. Ранее отдельно проверены fleet datasets10k/100k/500k/1m: их нельзя выдавать за1m результатов одного monitor. JSON serialization измерена отдельно (~1–3ms).

CPU steady43 samples: backend p95 14.99%/max16.82%, DB12.56%/35.97%, worker26.74%/39.61%. Docker MemUsage max backend75.93MB/DB75.64MB/worker70.64MB — sampled container usage, не RSS/не непрерывный peak. Fault snapshot12.48%/5.55%/1.98% и62.79/54.25/63.25MiB — единичный снимок, не распределение. Windows/Docker Desktop shared host, параллельная локальная активность; исходные детали в phase6-performance.md.

## Исправление атрибуции доказательств

Fault raw log содержит51 lifetime monitor UUID: сценарий удаляет один monitor и создаёт replacement. В initial/final DB snapshots по50 одновременно настроенных мониторов. Acceptance script сначала ошибочно предположил50 уникальных UUID во всём журнале; проверка остановилась, после чтения сценария исправлена на явный контракт51 lifetime/50 fleet, без изменения исходных результатов.

`phase6-load-db-snapshot.json` sample04:18:41Z и `phase6-load-browser.json` start04:19:04Z — **earlier** эксперимент. Финальный журнал475 стартов начинается04:22Z. Старые DB/browser файлы полезны отдельно (50 реальных строк/четыре ширины), но не подтверждают финальную475-серию или нынешнюю монохромную тему. Сам475-report содержит фактический SQL count и согласуется с raw events. Нынешние четыре viewport/12axe подтверждены отдельным Phase7 browser gate.

Стоимость новых пяти минут/больших DB fixtures не оправдана: production scheduling/SQL не изменены. Повторить эксперименты необходимо при изменении scheduler, claims, analytics, индексов, deployment limits или появлении нового симптома, а не ради свежей даты.
