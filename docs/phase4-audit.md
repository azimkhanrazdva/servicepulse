# Аудит Phase 4 перед Phase 5 — 20 октября 2026

**Вывод:** Phase 4 завершена в заявленном локальном объёме maintenance + transactional outbox +
SMTP/Mailpit. Подтверждённых BLOCKER/HIGH в этом объёме не найдено. Это не завершение всего
задания Mad Devs. Phase 5 не начата и ожидает отдельной команды владельца.

Проверен исходный HEAD `e03f5ed`, затем добавлены только проверки и документация аудита.
Ревью выполнено тем же агентом в отдельном проходе; независимое человеческое ревью не заявляется.
Результаты: [машинный отчёт](../artifacts/phase4-audit.json), [журнал](development-log.md).

## Основание и происхождение требований

Повторно прочитаны общие требования и задание 3 оригинального PDF, включая maintenance,
письма DOWN/RECOVERY, transient failures, два клиента, перезапуски и оставшиеся сценарии.
Mailpit допустим: работодатель прямо разрешает эмуляцию внешних сервисов, включая почту.
Transactional outbox, UUID leases, конкретный порог 2 и API CRUD — инженерные решения,
а не дословные отдельные требования работодателя.

Владелец сообщил, что отдельный подробный Phase 4 промпт не отправлял. Проверка обнаружила
`docs/prompts/004-phase4.md` и доступное прежнее вложение
`b42112d7-bbcc-40b8-a253-e31e87472024/Pasted text.txt`: оба имеют SHA-256
`25b32eb6eb718ee0dd56f6723b5aef524d1b47a90968eef19e7d0718075c5148`.
Файл впервые присутствует в реальном коммите `2a159d1`. Это проверяемый факт о сохранённом
вложении, без предположений о намерениях владельца и без создания новой истории получения.
Предыдущую запись журнала не переписывали. Основной критерий настоящего аудита — исходное
задание и master prompt. P4-xx оставлены как дополнительные инженерные критерии.

## Проверка реализации

| Область / ID | Фактический механизм | Доказательство |
| --- | --- | --- |
| Миграция 0004 / P4-21 | Четыре новые таблицы; XOR цели, интервалы, FK, уникальность событий/доставок и индексы. Старые incidents получают notifications_enabled=false; новые явно true | `backend/tests/run.py`: реальные fixtures 0001/0002/0003 → head и Alembic metadata check PASS; рабочая БД уже 0004 |
| MNT-01/02 | Версионированный CRUD для monitor/group, timezone-aware даты, UTC start <= now < end | CRUD/validation/boundary/cascade DB-тесты, maintenance.spec.ts |
| MNT-03/04, SCN-09 | Worker не зависит от suppression; сохраняются реальные DOWN, результаты и incident | Реальные HTTP-ошибки под maintenance в fault-suite; DOWN + отдельный badge в двух браузерах |
| MNT-05/07, SCN-10 | Union применимых окон; monitor подавляет все маршруты, group — собственные. Общий адрес может использовать независимую разрешённую группу | overlap, multi-group, frozen-recipient, preflight-after-claim DB-тесты; Mailpit 0 писем внутри контролируемого окна |
| MNT-06, SCN-11 | Reconciliation не зависит от следующего CheckResult | Реальное окончание окна: одно DOWN, список HTTP-результатов до/после совпадает |
| MNT-08 | Восстановление внутри окна без ранее отправленного DOWN отменяет устаревшую пару; ранее отправленный DOWN требует отложенного RECOVERY | DB-тест с обоими вариантами + две реальные Mailpit-ситуации |
| NTF-01/02/03 | Настройки групп; снимок адресов/маршрутов при подтверждении; DOWN и RECOVERY одного incident | Реальный SMTP и чтение принятых писем Mailpit API; браузерные receipt IDs |
| NTF-04/06 | Result/state/incident/event/routes/deliveries в одной DB-транзакции; unique(incident,type), unique(event,email) | SQL division-by-zero после flush откатывает всё; прямые unique violations; повторные ошибки не добавляют письмо |
| NTF-05/07 | Отдельный dispatcher; SMTP вне транзакций; persisted attempts/backoff, 4xx retry, 5xx terminal, token leases/SKIP LOCKED | DB concurrency/expiry/cancellation, новый terminal-550 тест; реальные остановки Mailpit/dispatcher/worker/PostgreSQL |
| NTF-08 | Логическая идемпотентность; SMTP acceptance не равно exactly-once/доставке в mailbox | Реальный crash после DATA до ack: 3 физических письма, 2 логические доставки |
| SCN-06/07 и уведомления | Стандартный порог 2, успех сбрасывает streak; первая ошибка не создаёт incident/outbox | Новый DB/worker/dispatcher тест: transient → success → transient → confirmed DOWN → повторные ошибки → RECOVERY |
| Два клиента / REL-04 | SSE полные snapshots, reconnect; maintenance GET и badge не ограничены только текущей страницей окон | Все 5 браузерных тестов PASS; maintenance содержит offline/online второго клиента |

`notification_routes.group_id` намеренно не FK: это исторический UUID снимка, не живая принадлежность.
Авторизация дополнительно соединяет текущие membership/recipients; удалённая группа не разрешает письмо.
Проверены порядок блокировок, границы транзакций, stale acknowledgements и административные закрытия.
Продуктовый код и миграция 0004 в ходе аудита не менялись.

## Фактически выполненные проверки

- Исходный backend: **107 PASS, 17,16 с**, без skips. После расширения: **109 PASS, 20,33 с**;
  fixtures миграций и metadata check PASS. Команда: `docker compose --profile test run --rm --build tests`.
- `ruff check backend scripts/phase4_fault_smoke.py` и `ruff format --check ...`: PASS.
- Из `frontend`: `npm test` — **15 PASS**; typecheck, lint, format:check, build — PASS;
  `npm audit --audit-level=high` — **0 vulnerabilities**.
- `npm run test:e2e` — **5 PASS, 17,0 с**, 0 skipped/flaky/unexpected. Реальные UI/API/worker/SMTP,
  два независимых browser context и reconnect; не имитация успешного backend.
- `python scripts/phase4_fault_smoke.py`: исходный повтор **PASS, 78,468 с**;
  после добавления проверки первого transient HTTP-сбоя **PASS, 78,781 с**, семь групп сценариев.
  Изолированный проект/volume удалён самим harness; основная БД не сбрасывалась.
- Обычный путь: одно DOWN и одно RECOVERY, общий адрес двух групп без повторов.
  SMTP outage: 2 попытки с тем же delivery ID; acceptance-crash: 3 физических/2 логических.
- Исторические smoke >30 s/restart/proxy не запускались повторно в этом аудите: их прошлые
  результаты остаются историческими доказательствами для неизменённого продуктового кода.

Ошибки команд аудита: первый вывод PDF столкнулся с cp1251; `python -X utf8` исправил вывод.
`npm audit` из корня завершился ENOLOCK; запуск из `frontend` с существующим lockfile прошёл.
Тесты не удалялись и assertions не ослаблялись. Перезаписанные test reports — новые реальные
измерения; предыдущие версии и значения доступны в Git, а исходный checkpoint остаётся историческим.

## GitHub и границы CI

[PR #3](https://github.com/azimkhanrazdva/servicepulse/pull/3) открыт, база `feat/incident-lifecycle`,
цепочка #1 → #2 → #3 сохранена. На входе `head=e03f5ed`, MERGEABLE, reviews=[]:
успешные checks не означают, что кто-либо уже провёл человеческое ревью.
[PR CI 39381498023](https://github.com/azimkhanrazdva/servicepulse/actions/runs/39381498023)
прошёл для точного e03f5ed: 107 backend (11,89 с), 15 frontend, migrations/lint/format/types/build/audit.
Браузерный E2E и изолированные процессные fault-сценарии выполняются локально, не в этом workflow.
Новый audit-коммит будет отправлен в ту же ветку; последующие checks проверяются отдельно.
Репозиторий приватный; merge, изменение bases и публичная публикация не выполнялись.

## Найденные недоработки и ограничения

- **MEDIUM, известная политика:** ещё не авторизованный DOWN отменяется, если сервис успел
  восстановиться до dispatcher, даже вне maintenance. Тогда и RECOVERY не отправляется;
  incident остаётся в журнале. Это подтверждено тестом `test_recovered_before_down_send_cancels_both`,
  а не потеря транзакционной записи. Следовательно, безусловную гарантию «письмо о каждом
  подтверждённом инциденте после любого простоя dispatcher» заявлять нельзя. Для такого SLA
  потребуется отдельно изменить политику исторических уведомлений; здесь она сохранена явно.
- **MEDIUM:** после 8 неуспехов или постоянного SMTP-отказа доставка FAILED; автоматического
  восстановления после неограниченного простоя и ручного retry UI нет. Есть диагностический API.
- **MEDIUM, граница SMTP:** уже авторизованную отправку нельзя отозвать при новом maintenance,
  pause, удалении или изменении получателей; crash после acceptance может дать физический дубль.
  Абсолютное подавление уже летящего DATA и exactly-once не заявляются.
- **MEDIUM, deployment scope:** только доверенная локальная среда и Mailpit; production SMTP
  TLS/auth, внешняя mailbox-доставка, rate limits и публичная management API не проверены.
- **LOW, исправлено:** тесты уведомлений почти всегда задавали threshold=1. Добавлены default-2
  lifecycle+outbox regression и terminal-550 dispatch regression; живой harness проверяет первую ошибку.
- **LOW, исправлено:** устаревшие текущие статусы PR и часть acceptance-строк обновлены;
  provenance сохранённого вложения отдельно проверен. Исторические записи не переписываются.
- **LOW:** предупреждения GitHub Actions о Node runtime/ubuntu image; не падения CI.

## Что ещё обязательно для всего задания

| Сценарий | Статус на этом checkpoint |
| --- | --- |
| SCN-01 | PASS: dashboard автоматически, повторный browser run |
| SCN-02 | TODO: автообновление публичной страницы |
| SCN-03/04/05 | PASS: normal SMTP DOWN/RECOVERY без повторов; оговорки выше обязательны |
| SCN-06/07/08 | PASS: threshold, transient, закрытие incident; новый интеграционный regression |
| SCN-09/10/11 | PASS в описанной границе авторизации: HTTP продолжается, suppression, позднее DOWN |
| SCN-12 | Исторический PASS обычного >interval запроса; не гарантия при произвольной приостановке процесса сверх lease |
| SCN-13 | TODO: измеренный sustained 50 × 30 s |
| SCN-14 | Исторический PASS mixed slow/fast pair; 50-load отдельно |
| SCN-15 | TODO: быстрый месячный запрос на большом dataset |
| SCN-16 | TODO: публичная проекция и privacy tests |
| SCN-17 | PASS сохранённых settings/incident/queue: исторические restart smoke + нынешний fault run |
| SCN-18 | PARTIAL: нет искусственных observation failures; отображение пробелов на графике ещё TODO |

Также отсутствуют графики и availability 24h/7d/30d. Это последующие фазы, не ошибки готового
maintenance/outbox. Следующий разрешаемый шаг — Phase 5 UI/history/public projection с изоляцией
публичных REST/SSE payloads от management, coverage-aware данными и тестами приватности.
До отдельной команды владельца никаких компонентов Phase 5 не создавать.
