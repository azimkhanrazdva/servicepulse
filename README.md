# ServicePulse

ServicePulse проверяет доступность сайтов, хранит наблюдения и инциденты, отправляет уведомления и публикует разрешённые владельцем статусы. Проект выполнен для задания №3 MadDevs на Junior Agentic Developer. Backend и frontend работают отдельно; метрики рассчитываются из реальных HTTP-проверок.

Текущая версия: кандидат v1.0 с русским административным и публичным интерфейсом. Официальная отправка работодателю требует решения владельца. Итоговые таблицы, свежие проверки, ограничения и план до 26 октября: [отчёт владельцу](docs/OWNER_FINAL_REPORT_RU.md). Старые проверки не выдаются за результаты текущего перевода.

## Возможности

- Создание, редактирование, удаление, пауза, возобновление и ручной запуск мониторов.
- Интервал 30–3600 с, таймаут 0,1–120 с, ожидаемый HTTP-код и необязательный текст ответа.
- Подтверждение падения после двух последовательных ошибок по умолчанию; порог настраивается.
- Группы, общий статус, адресаты уведомлений, monitor/group maintenance и продолжение проверок во время обслуживания.
- Журнал инцидентов, автоматическое восстановление, длительность падения и отдельные административные закрытия.
- Transactional Outbox, логическая дедупликация, сохранённые попытки и SMTP через локальный Mailpit.
- SSE-обновления двух независимых клиентов, восстановление соединения и полная синхронизация.
- Отдельная публичная страница/API/SSE: явное разрешение каждого сервиса и отдельное разрешение истории.
- Доступность за 24 ч/7 д/30 д, график времени ответа, покрытие наблюдениями и честное «НЕТ ДАННЫХ».

## Стек и архитектура

Python3.12, FastAPI, Pydantic, SQLAlchemy2, Alembic, PostgreSQL17, HTTPX/asyncio; React19, TypeScript, Vite, nginx. Отдельные процессы API, public API, worker и SMTP dispatcher. Redis/Celery/Kafka/Kubernetes не требуются. PostgreSQL хранит настройки, leases, результаты, инциденты, окна, публикации и outbox. [Архитектура](docs/architecture.md), [решения](docs/decisions.md).

## Требования и запуск

Docker Engine/Desktop с Linux containers и Docker Compose. Проверенная среда предыдущего этапа: Compose5.5.1; изолированный acceptance harness использует !override и требует 2.24.4+. Свободные локальные порты:8080,8000,8081,8025. Первое получение образов/зависимостей требует интернета. Для обычного запуска host Python/Node не нужны; для тестовых скриптов нужны Python3.11+, Node24 и Chromium.

Репозиторий публичный по явному решению владельца от 21 октября 2026. Выберите актуальную ветку проверки `codex/russian-submission`: в `main` остаётся ранняя версия 0.1. Снимок до исправления CI: [`7dae3d2`](https://github.com/azimkhanrazdva/servicepulse/commit/7dae3d230b3e38527e78ad6dc117a451605ff4f6); исправление `datetime-local` находится в следующих commits этой ветки.

```powershell
git clone https://github.com/azimkhanrazdva/servicepulse.git
cd servicepulse
git switch codex/russian-submission
if (-not (Test-Path .env)) { Copy-Item .env.example .env }
docker compose up -d --build --wait
```

В Linux/macOS подготовка конфигурации: `[ -f .env ] || cp .env.example .env`; команда Compose та же. Существующую .env не перезаписывайте. Миграции выполняются перед запуском API/worker. Приложение пустое до создания мониторов; seed создаёт настройки, а не наблюдения.

| Адрес | Назначение |
|---|---|
| http://localhost:8080 | Управление |
| http://localhost:8000/docs | OpenAPI, технические поля API на английском |
| http://localhost:8025 | Локальные письма Mailpit |
| http://localhost:8081/status/your-slug | Публичная страница после явного opt-in |

Корень 8081 намеренно возвращает 404: списка закрытых страниц нет. `docker compose ps --all` показывает контейнеры и migration job. Остановка: `docker compose stop`; продолжение: `docker compose up -d`. **Не удаляйте volumes**: в них история и настройки. Управление не имеет авторизации и привязано к 127.0.0.1; не открывайте 8000/8080/Mailpit в интернет.

## Конфигурация

| Переменная | Значение примера / смысл |
|---|---|
| POSTGRES_DB / POSTGRES_USER | servicepulse; локальные тестовые значения |
| POSTGRES_PASSWORD | local-development-only; не использовать в production |
| DATABASE_URL | Compose формирует DSN; можно задать для host-разработки |
| SIMULATOR_ORIGIN | .env.example явно разрешает только http://simulator:8090; безопасный default кода пустой |
| SMTP_HOST / SMTP_PORT | mailpit /1025, без внешней пересылки |
| SMTP_SENDER | servicepulse@example.com, локальный отправитель |
| SMTP_TIMEOUT_SECONDS |5 с; допустимо 0,1–10 с |
| CONCURRENCY |50 по умолчанию,1–100; переопределять в shared backend environment Compose |
| MAX_BODY_BYTES |1048576 по умолчанию; максимум 10MiB, переопределять в environment |

.env исключена из Git. Настоящие SMTP-ключи не нужны. Исключение simulator не разрешает произвольные private/local адреса.

## Проверяемая демонстрация

Создайте монитор http://simulator:8090/target/acceptance-demo, ожидаемый 200, текст ServicePulse ready, интервал 30 с. Worker выполнит настоящий HTTP-запрос и запишет результат. Создайте группу с локальным адресатом demo@example.com. Изменяйте только свой именованный target:

```powershell
python scripts/simulator_control.py acceptance-demo --status 500
python scripts/simulator_control.py acceptance-demo --status 200
python scripts/simulator_control.py acceptance-demo --delay 10
python scripts/simulator_control.py acceptance-demo --delay 0
```

Для подтверждения DOWN нужны две завершённые ошибки, затем успешная проверка закрывает инцидент и создаёт RECOVERY. Повторные ошибки одного инцидента не создают новые логические DOWN. Simulator поддерживает 404/500, задержку, текст и redirect; разрыв соединения проверяется остановкой изолированного simulator, а не вымышленным ответом. `python scripts/seed.py` создаёт только настройки; `python scripts/smoke.py` использует и удаляет только свой монитор. Полный [сценарий 5–10 мин](docs/demo-script.md).

## Семантика и ограничения

UNKNOWN до первого наблюдения; UP после успеха; DOWN после порога; PAUSED блокирует новые запуски. Возобновление возвращает UNKNOWN. Любое редактирование сбрасывает текущий статус/серию ошибок, сохраняет историю и закрывает открытый инцидент CONFIG_CHANGED. Пауза закрывает PAUSED. Эти закрытия не означают успешное восстановление. Группа игнорирует PAUSED, затем выбирает DOWN > UNKNOWN > UP; пустая UNKNOWN, все pausedPAUSED.

Расписание fixed-delay: окончание сохранения + интервал; нельзя требовать ровно 500 результатов за 300 с. PostgreSQL leases/UUID fencing и config_version препятствуют пересекающимся запускам и записи устаревшего результата. Простой сервера создаёт пропуск наблюдений, а не ложный DOWN.

Доступность = успешные / наблюдаемые проверки, включая обслуживание и разные версии настроек. Покрытие времени показано отдельно; отсутствие наблюдений не равно 100%. Legacy cadence неизвестна. SQL возвращает не более 288/336/360 buckets для 24 ч/7 д/30 д; последние отдельные результаты ограничены 100. Мониторы/группы и dashboard selection ограничены 500; глобальный список сверх этого лимита не реализован.

Maintenance использует start <= now < end; окна пересекаются, проверки продолжаются, статус остаётся реальным. Окно монитора подавляет все маршруты, окно группы только её маршруты. Dispatcher пересматривает eligibility независимо от новых результатов. Если сайт остаётся DOWN после конца окна, уведомление становится обязательным. Полностью подавленный maintenance-only инцидент не порождает устаревшую пару.

Новые 0006 incidents сохраняют обязательную пару DOWN→RECOVERY вне maintenance даже при задержке dispatcher/быстром восстановлении. Legacy unknown eligibility не угадывается и не рассылается задним числом. Логические события/доставки уникальны по incident/type и event/email; адреса нормализуются, получатели фиксируются при подтверждении, удаление маршрутов отзывает ожидание. SMTP вне DB transaction; уже отправляемое письмо отозвать нельзя. Retry5–300 с, максимум 8 попыток; постоянный отказ/исчерпание дают FAILED. SMTP acceptance не доказывает получение ящиком: crash-after-accept-before-ack может дать физический дубль. Требование exactly-once SMTP не заявляется.

## API и публичность

| Маршруты | Назначение |
|---|---|
| GET /api/health, /api/ready | Процесс и готовность DB/schema |
| /api/monitors | CRUD; /{id}/pause, /resume, /run, /results, /incidents, /analytics |
| /api/groups | CRUD, состав и адресаты |
| /api/incidents | Журнал, фильтры, pagination; /active и /{id} |
| /api/maintenance | Versioned CRUD окон |
| /api/notifications | Ограниченная диагностика доставок |
| /api/events | Administrative SSE snapshots каждые 2 с |
| /api/status-pages | Управление страницами/согласием владельца |
| /api/public/pages/{slug} | Отдельная безопасная публичная проекция |
| /api/public/pages/{slug}/events | Публичный SSE с повторной проверкой прав |
| /api/public/pages/{slug}/services/{public_id}/analytics | История только при show_history |

PUT/pause/resume требуют config_version; конфликт 409 сохраняет черновик. Monitor DELETE без версии оставлен для ранних скриптов и безусловен; UI передаёт версию. Group DELETE требует версию. Public IDs не равны monitor UUID. Закрытые/неизвестные страницы и запрещённая история дают generic404. URL, private name, email, raw errors, windows и outbox не публикуются. Отзыв проверяется при каждом запросе/tick; уже полученные байты вернуть невозможно. Публичная DB роль пока общая с management; read-only transactions не заменяют least privilege.

## Тестирование и реальные результаты

```powershell
docker compose --profile test run --rm --build tests
python -m ruff check backend
python -m ruff format --check backend
cd frontend
npm ci
npx playwright install chromium
npm run typecheck
npm run lint
npm run format:check
npm test
npm run build
npm run test:e2e -- --workers=2
```

DB-тесты используют только servicepulse_test; runner проверяет имя и совпадение URL перед fixture reset. Основной volume не сбрасывается. Миграции 0001–0006 проверяют сохранность старых monitor/results/groups/incidents/outbox/windows/publication/cadence; отсутствующая eligibility не восстанавливается. Host pytest без TEST_DATABASE_URL пропускает DB-тесты и не является полной проверкой. Свежие результаты русского этапа находятся в отчёте владельцу и artifacts/ru-*; Phase7 150/32/12 и предыдущие load reports остаются историческими.

Длительные эксперименты: scripts/phase6_load.py, phase6_fault_load.py, phase6_cold_history.py. Сохранённые данные:475steady/295fault; dense100000rows/360buckets, coldmax635 мс/warmp95867 мс/max1180 мс. Это отдельные измерения 20 октября на sharedDockerhost; не универсальная гарантия<1 с. Подробности: [производительность](docs/phase7-performance.md). Изменение языка само по себе не требует нового дорогого load test.

## Безопасность

HTTP(S), проверка всех DNS ответов, блокировка nonglobalIP, numeric pinning + исходные Host/SNI, запрет redirect/environmentproxy/compression, общий deadline и bodylimit. Management только loopback. Реальный внешний TLS/certificate стенд, auth/RBAC, rate/SSElimits, egressfirewall, выделенная publicDBrole, productionSMTP/TLS и backupdrills остаются дальнейшей работой. Полной WCAG/security/production сертификации нет. Worker/dispatcher пишут JSON, API пока Uvicorntext. Полная state-transitiontimeline сверх check/incidentjournal не реализована.

## GitHub, AI и следующий шаг

Репозиторий публичный по явной команде владельца от 21 октября. PR#1–4 существуют и не объединены; новые PR/merge/release требуют разрешения. Актуальная ветка — [codex/russian-submission](https://github.com/azimkhanrazdva/servicepulse/tree/codex/russian-submission), в main остаётся 0.1. [Исправление CI и проверка доступа](docs/ci-datetime-fix.md), [порядок GitHub](docs/github-workflow.md), [журнал](docs/development-log.md), [план](docs/roadmap.md), [передача](docs/submission-guide.md).

Инструмент OpenAI Codex; модель **solana 6.1 - medium по данным владельца от 21 октября 2026**, без независимого технического подтверждения. Codex использовался для работы с файлами, тестами и Git; владелец задаёт требования и утверждает результат. [AI disclosure](docs/ai-development.md), реальные [промпты](docs/prompts/README.md). Эссе остаётся черновиком до утверждения. Письма работодателю не отправляются агентом.

Проект написан с пустого workspace без чужого application template. Использованы FastAPI/Pydantic/SQLAlchemy/Alembic/asyncpg/HTTPX/httpcore/Uvicorn, React/TypeScript/Vite, pytest/Vitest/TestingLibrary/Playwright/axe/Ruff/Prettier, PostgreSQL/nginx/DockerCompose/Mailpit. Графики собственные SVG; SMTP основан на stdlib smtplib/EmailMessage. Чужие UI/assets не копировались; лицензии зависимостей остаются их лицензиями, лицензию проекта владелец ещё не выбрал. Проверяющему нужны ссылка на актуальную ветку, запуск и честное описание ограничений, а не вымышленная история.
