# Инженерные решения

Русская актуальная редакция; подробные исходные ADR и их реальная последовательность сохранены в Git:f3866cd. Таблица описывает принятые решения, не создаёт новые даты прошлых событий.

| Контекст | Решение | Альтернативы | Компромисс и последствия |
|---|---|---|---|
| Клиент-серверный продукт | FastAPI/Python3.12, React/TS, PostgreSQL | Go/Node/Vue | Стек владельца; отдельные процессы, общий DB источник правды |
| Регулярные asyncHTTP | Небольшой asyncio scheduler с PostgreSQLclaims/leases/UUIDfencing | APScheduler, Celery/Redis | Fixed-delay/ограниченная конкурентность; без лишнего broker. Нет distributedexactly-once |
| Два клиента/живые статусы | SSE полные снимки каждые 2 с | WebSocket/polling | Односторонних обновлений достаточно; дополнительное DB чтение, reconnect полная синхронизация |
| Краткая ошибка | Две последовательные ошибки, порог 1..10 настраивается | Первая ошибка DOWN, сложная degradedmodel | Меньше ложных инцидентов, confirmation задержка; UNKNOWN до наблюдений |
| Конкурентные изменения | config_version/409 + locks/fencedcompletion | Last-write-wins | Черновик сохраняется; edit сбрасывает текущую метрику, история остаётся |
| Инциденты | Uniqueopenmonitorindex, атомарный result/state/incident/outbox | In-memory состояние | Restart без фиктивных наблюдений; administrativeclosures не RECOVERY |
| Email | TransactionalOutbox + uniqueevent/delivery + frozenroutes | SMTP внутри DBtransaction | Логическая дедупликация; physicalduplicates после acceptancecrash возможны |
| Maintenance | Реальный статус отдельно от alertpolicy, reconciliation без CheckResult | Остановить проверки, считать UP | Наблюдения продолжаются; endwindowDOWN получает obligation |
| Быстрое восстановление |0006persistedeligibility/requiredDOWN | Отменять всю очередь при восстановлении | Исправляет ACC-EMAIL-01 для новых incidents; legacyunknown не угадывается |
| SSRF | Все DNSanswers проверены, numericpin+Host/SNI, no redirects/proxies | Проверить только URL/первый IP | Narrow simulatororiginopt-in; TLS интеграционныйстенд и egressfirewall будущаяработа |
| Публичность | Отдельные ASGI/build/nginx, explicitprojection/consent, show_historyopt-in | Общий adminAPI скрытьв UI | Нет private полей; sharedDBrole покасталобы production риском |
| Аналитика | Наблюдаемая доступность+отдельно coverage, boundedSQLbuckets | Предположить UP между проверками, загрузить всё в ORM | NO DATA честное; limit360 точек, legacycadence не backfill |
| DensehistoryJIT | SET LOCAL jit=off внутри analytics transaction | Глобально отключить JIT, миграция/partitioning | Не меняет семантику; измерен warmp95867 мс/max1180 мс, sort остаётся |
| Дизайн | Единый чёрно-белый CSS, nativeforms/SVG | Новая UI/chart библиотека | Компактный локальный продукт; axe не WCAG сертификация |
| Русский язык 21 октября | Локализовать представление, nativevalidation и SMTPbody; API неизменен | Полная i18n платформа | Один язык без зависимостей; optionvalues/headers/enumcodes сохраняются |
| История доказательств | Русская редакция архивов со ссылкой на f3866cd, исходные промпты и rawartifacts не тронуты | Переписать прошлые события/объявить старый тест новым | История проверяема, новые отчёты несут свои фактические время/команды |

Открытые решения владельца: лицензия проекта, employeraccess, создание следующих PR/merge и окончательная отправка. Модель раскрыта по данным владельца, без техподтверждения. Эссе требует утверждения.
