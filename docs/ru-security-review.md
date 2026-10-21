# Проверка безопасности русской версии,21октября2026

Проверяется доверенное локальное развёртывание. Production management без авторизации не допускается. Новая локализация не меняет URL-политику, TLS verify, public permissions, schema, leases и outbox policy. Использованы рекомендации security-best-practices для Python/FastAPI и React; новый отдельный независимый reviewer не заявляется.

| ID / приоритет | Наблюдение | Решение / доказательство |
|---|---|---|
| RU-SEC-01 / значимый advisory, применимость не доказана | Свежий pip-audit отметил certifi2026.10.18 по PYSEC-2026-4320/GHSA-6q48-6c7w-9gw2 и предложил2026.10.19. Upstream advisory, наоборот, называет2026.10.18 patched. Это расхождение источников, не доказательство эксплуатации установленной версии | Сохранён ru-pip-audit-before.json; pin обновлён до опубликованной2026.10.19, без других обновлений и без отключенияTLS. После обновления требуются новыйscan/rebuild/backend/browser/cleanruntime gates |
| RU-SEC-02 / граница | Общая роль PostgreSQL у admin/public; read-only transactions и отдельные ASGI/build/nginx не заменяют least privilege | Public privacy/revoke/route isolation проверяются PostgreSQL и настоящим Chromium. Выделенная роль остаётся roadmap |
| RU-SEC-03 / граница | Management безauth, допустим толькоlocalhost | Loopback bindings/TrustedHost/nginx проверены;8GET Host/route cases PASS. Не открывать8000/8080/Mailpit в интернет |
| RU-SEC-04 / неполная дополнительная проверка | Нет отдельного живого TLS/SNI/certificate стенда | Numeric pinning/Host/SNI/mockDNS тесты остаются, SEC-04 PARTIAL. Patch truststore не является доказательством всех TLS-сценариев |
| RU-SEC-05 / ограничение | SMTP после acceptance-before-ack может повторить физическое письмо | Семь новых fault-сценариев подтверждают logicaldedup;3physical/2logical не скрыты. Это не exactly-once SMTP |
| RU-SEC-06 / проверено в локальной модели | Русские API errors не показывают rawserverdetail, network/JSONошибки локализованы, cause сохраняется для отладки |150backend + новыеcomponentрегрессии; API error status/enum/fieldnames не меняются. React выводит текст без unsafeHTML |

Источники RU-SEC-01: [upstream advisory](https://github.com/certifi/python-certifi/security/advisories/GHSA-6q48-6c7w-9gw2), [опубликованная версия PyPI](https://pypi.org/project/certifi/2026.10.19/). Advisory помечен Critical для компрометации CA keys; пакет представляет публичный truststore, реальные секреты владельца не использовались. Автоматический поиск известных advisory не доказывает абсолютную безопасность. Actual результаты после patch находятся в OWNER_FINAL_REPORT_RU.md и ru-pip-audit.json, а исходное несовпадение не удаляется из истории.
