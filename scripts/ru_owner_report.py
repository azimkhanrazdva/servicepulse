"""Render owner tables from the checked per-ID ledger, not subjective percentages."""

from datetime import UTC, datetime, timedelta, timezone

from ru_acceptance import ROOT, read, russian_typography


def render_owner_report():
    report = read("artifacts/ru-readiness.json")
    now = (
        datetime.now(UTC)
        .astimezone(timezone(timedelta(hours=5)))
        .isoformat(timespec="seconds")
    )
    descriptions = {
        "Backend": (
            "FastAPI, CRUD, version409, группы и health",
            "150 PostgreSQL/backend тестов, атомарность и конфликты",
            "API access logs ещё текстовые; JSON worker/dispatcher есть",
        ),
        "Frontend": (
            "Русские admin/public, формы, ошибки, статусы, даты и native validation",
            "35 component и12 Chromium; реальные действия и SSE",
            "Полный state timeline; глобальные counters/pagination сверх500",
        ),
        "PostgreSQL": (
            "Schema0006, FK/constraints/indexes, persistence",
            "Fresh/legacy migrations и новая изолированная DB",
            "В обязательном локальном объёме остатка нет; production backups/role hardening отдельно",
        ),
        "Мониторинг": (
            "Async HTTPX, fixed-delay, leases/fencing, threshold/incidents",
            "Свежие HTTP/ручной запуск/restart; сохранённый50×30 опыт отдельно",
            "Дополнительные типы проверок и регионы вне объёма",
        ),
        "Уведомления": (
            "Русские письма, persisted outbox/routes/retry и maintenance",
            "Реальный Mailpit, DOWN→RECOVERY,7fault-групп и delayed/refused pair",
            "External SMTP не проверяется; finite retry/physical duplicate ambiguity остаются",
        ),
        "Аналитика": (
            "24ч/7д/30д, SQL buckets, coverage и НЕТ ДАННЫХ",
            "Свежая регрессия; raw100k/360buckets benchmark20октября",
            "Warm outlier1180мс; нет универсальной гарантии<1с",
        ),
        "Безопасность": (
            "SSRF/Host/public isolation; patch certifi после scan",
            "150backend/12browser privacy; актуальные npm/pip scans",
            "Live external TLS fixture; auth/least-privilege/rate/egress перед production",
        ),
        "Тестирование": (
            "Регрессия, migration fixtures, realbrowser/SMTP/clean runtime",
            "150/35/12,12axe0violations; точный CI проверяется отдельно",
            "Полная WCAG/production сертификация не заявляется",
        ),
        "GitHub": (
            "Приватный repo, настоящие commits,3 существующих PR, prepared stack",
            "Ветки и ancestry сохраняются, обычный проверенный push",
            "Employer read access; новые PR/merge только по решению владельца",
        ),
        "Документация": (
            "Русская README, архитектура, гайды, матрица, история и draft essay",
            "Пер-ID доказательства, автоматическая проверка10предложений",
            "Личное утверждение эссе и финальная отправка владельцем",
        ),
    }
    lines = [
        "# ServicePulse v1.0 — итоговый отчёт владельцу",
        "",
        f"Сформирован: {now}, Asia/Qyzylorda. Дата подготовки —21октября2026, срок сдачи —26октября2026.",
        "",
        "**Техническая демонстрация проверена. Пакет готов к рассмотрению владельцем; официальная отправка не выполнена.** Подготовка документации не означает SUBMITTED. Письмо работодателю, merge, смена приватности и удаление пользовательских данных не выполнялись.",
        "",
        "## 1. Готовность по разделам",
        "",
        "Процент — PASS/(PASS+PARTIAL+FAIL+NOT VERIFIED)×100 по явному набору ID, перечисленному ниже. PARTIAL не получает полного балла; NOT APPLICABLE исключается только с обоснованием. OPT исключены из обязательных процентов. Разделы — пересекающиеся представления реестра: их проценты нельзя складывать или усреднять для оценки работодателя.",
        "",
        "| Раздел | Что сделано | Что работает | Что осталось | Статус | Готовность, % |",
        "|---|---|---|---|---|---:|",
    ]
    for name, values in descriptions.items():
        section = report["sections"][name]
        status = (
            "PASS"
            if section["counts"].get("PASS", 0) == section["denominator"]
            else "PARTIAL"
        )
        if section["counts"].get("NOT VERIFIED", 0):
            status += " / NOT VERIFIED"
        lines.append(
            "| "
            + " | ".join(
                [
                    name,
                    *values,
                    status,
                    f"{section['percent']:.2f} ({section['counts'].get('PASS', 0)}/{section['denominator']})",
                ]
            )
            + " |"
        )
    lines += [
        "",
        "### Проверяемый знаменатель каждого раздела",
        "",
        "| Раздел | ID, по которым рассчитана доля |",
        "|---|---|",
    ]
    for name, section in report["sections"].items():
        lines.append("| " + name + " | " + ", ".join(section["ids"]) + " |")
    lines += [
        "",
        "## 2. Требования MadDevs и дополнительные критерии",
        "",
        "В реестре232 связанных критерия проекта, а не232 независимых требования работодателя. M — работодатель, O — владелец, T — инженерный критерий, OPT — допустимый необязательный выбор. Полная русская таблица: [phase7-final-acceptance.md](phase7-final-acceptance.md); машинный расчёт: [ru-readiness.json](../artifacts/ru-readiness.json).",
        "",
        "| Источник | Всего | PASS | PARTIAL | FAIL | NOT VERIFIED | NOT APPLICABLE | Строгая доля, % |",
        "|---|---:|---:|---:|---:|---:|---:|---:|",
    ]
    for origin, summary in report["origins"].items():
        c = summary["counts"]
        lines.append(
            f"| {origin} | {sum(c.values())} | "
            + " | ".join(
                str(c.get(k, 0))
                for k in ["PASS", "PARTIAL", "FAIL", "NOT VERIFIED", "NOT APPLICABLE"]
            )
            + f" | {summary['percent']:.2f} |"
        )
    mandatory = report["mandatory_project"]
    lines += [
        "",
        f"**Обязательные требования работодателя: {report['origins']['M']['percent']:.2f}% ({report['origins']['M']['counts'].get('PASS', 0)}/72 PASS).** Остаток M — DEL-18: фактический доступ работодателю к приватному репозиторию не проверен. GEN-07 теперь раскрыт с явным источником модели: это подтверждение честного disclosure, не техническая идентификация deployment. Русская README не нарушает языкового требования работодателя: English был ранним предпочтением владельца и заменён новым запросом.",
        "",
        f"Проектные критерии без OPT: **{mandatory['percent']:.2f}%**. Эта математическая доля не вероятность отсутствия ошибок и не субъективная оценка красоты. Демонстрационный сценарий имеет PASS в заявленной локальной границе. Готовность к официальной передаче зависит от личного утверждения эссе, проверки версии/ограничений, read access и решения об отправке.",
        "",
        "## 3. Свежие проверки21октября",
        "",
        "| Команда / проверка | Фактический результат | Доказательство |",
        "|---|---|---|",
    ]
    tests = [
        (
            "docker compose up -d --build --wait",
            "PASS; работающие API/frontend/DB/worker/dispatcher/public/Mailpit, без reset volumes",
            "ru-clean-checkout.json; localhost8080",
        ),
        (
            "docker compose --profile test run --rm --build tests",
            "150 PASS; legacy0001..0005→0006, Alembic без новых операций",
            "ru-backend-tests.xml",
        ),
        (
            "npm test",
            "35 PASS;3 новых проверки русского отображения/API errors/native validation",
            "ru-component-tests.json",
        ),
        (
            "npm run test:e2e -- --workers=2",
            "12 PASS;0 skipped/flaky/unexpected, дваadmin+дваpublic клиента, реальныеHTTP и письма",
            "ru-browser-tests.json; ru-release-journey.json",
        ),
        (
            "TypeScript / ESLint / Prettier / build / Ruff",
            "PASS после исправления пойманных lint/format ошибок",
            "development-log.md; текущий CI",
        ),
        (
            "Четыре viewport и axe",
            "390×844,768×1024,1440×900,1920×1080;12scans/0violations",
            "ru-accessibility-*.json; output/playwright/ru",
        ),
        (
            "node scripts/ru_ui_audit.cjs",
            "Статические JSX/aria/placeholder проверены; technical names разрешены",
            "ru-ui-audit.json",
        ),
        (
            "phase4_fault_smoke.py с ru-prefix",
            "7групп PASS;SMTP outage/retry/restart/maintenance/crash, logicaldedup",
            "ru-smtp-faults.json/log",
        ),
        (
            "python scripts/phase6_email_smoke.py",
            "2группы PASS; delayed dispatcher/quick recovery/refusal, тот жеID и порядок",
            "ru-email-continuation.json",
        ),
        (
            "phase7_clean_checkout.py --ref codex/russian-submission",
            "PASS: committed clone, новаяDB0006, HTTP/history/groups/restarts/fulljourney; общийhost/cache раскрыт",
            "ru-clean-checkout.json; ru-clean-browser.json",
        ),
        (
            "Host/public route probes",
            "8 реальных GET случаев PASS",
            "ru-host-guard.json",
        ),
        (
            "npm audit / pip-audit",
            "0 known после certifi pin refresh; исходныйscan с1 finding сохранён",
            "ru-npm-audit.json; ru-pip-audit-before.json; ru-pip-audit.json",
        ),
    ]
    for command, result, proof in tests:
        lines.append(f"| {command} | {result} | {proof} |")
    ci_path = ROOT / "artifacts/ru-ci.json"
    if ci_path.exists():
        ci = read("artifacts/ru-ci.json")
        lines += [
            "",
            f"Hosted CI snapshot: [{ci['databaseId']}]({ci['url']}) для **{ci['headSha']}**, все3jobs SUCCESS; скачанный browser artifact проверен. Последующий handoff-only commit получает отдельную live exact-SHA проверку после push; snapshot не приписывается новому hash. Итоговый run указывается в финальном ответе и доступен в Actions без бесконечного commit→proof→commit цикла.",
        ]
    else:
        lines += [
            "",
            "**CI нового русского этапа пока NOT VERIFIED.** Зелёный Phase7 run20октября не засчитывается за новый код. После проверенного приватного push требуется actual exact-SHA run и downloaded browser artifact.",
        ]
    lines += [
        "",
        "## 4. Что было неуспешно и что исправлено",
        "",
        "| Наблюдение | Исправление / граница |",
        "|---|---|",
        "| После перевода15старых component ожиданий не совпали с UI | Русские labels и regex обновлены; assertions поведения сохранены; тесты не удалялись |",
        "| Широкая замена в тестах затронула4imports и EventSource stub | Typecheck/tests обнаружили ошибку; imports восстановлены изGit, технические globals сохранены |",
        "| Переведённый maintenance option мог отправить русское значение | Явные value=ACTIVE/UPCOMING/ENDED сохраняют API enum; display отдельно |",
        "| ESLint потребовал cause у network error; Prettier отметил тест | Cause добавлен, форматирование исправлено, gates повторены |",
        "| pip-audit отметил certifi2026.10.18, upstream называет эту версию patched | Источники расходятся;2026.10.19 опубликована и закреплена. Не заявляется доказанная эксплуатация18; postscan0known и rebuild/regression выполнены |",
        "",
        "Security sources: [upstream advisory](https://github.com/certifi/python-certifi/security/advisories/GHSA-6q48-6c7w-9gw2), [PyPI2026.10.19](https://pypi.org/project/certifi/2026.10.19/). Обоснование и границы: [ru-security-review.md](ru-security-review.md).",
        "",
        "## 5. Сохранённые измерения20октября, не новые load tests",
        "",
        "| Эксперимент | Результат | Ограничение |",
        "|---|---|---|",
        "| Steady50×30с/300с |475HTTP/475DB,375success/100expectedfail, max41,0overlap; steady delay p95552мс | Fixed-delay, не обещанные500запусков; раннийbrowser/DBsnapshot относится к другому прогону |",
        "| Fault-under50 |295HTTP/max17/0overlap; delay p951,740с; worker16,547с/DB22,360с recovery |51 lifetimeUUID из-за замены1monitor, initial/finalfleet50; shutdown290DB против289 live |",
        "| Dense monthly |100000rows одногоmonitor/360buckets;3cold/21warm, coldmax635мс, warmp95867мс/max1180мс | OS cache/sharedhost; не HTTP SLA и не universal<1s |",
        "",
        "Исходные данные переанализированы; scheduler/SQL не менялись при переводе. Certifi pin влияет на truststore, а не планировщик/агрегацию; новый TLS benchmark не выдумывается. Raw proof и scope: phase7-performance.md и ru-performance-reference.json.",
        "",
        "## 6. Известные ограничения",
        "",
        "| Ограничение | Что это означает |",
        "|---|---|",
        "| Локальное управление безauth | Не открывать management8000/8080/Mailpit в интернет; public толькоотдельныйingress |",
        "| Shared public DB role | Read-only transactions/allowlist не заменяют отдельные DB privileges |",
        "| SMTP uncertainty и8attempts | Возможен физический дубль послеacceptancecrash; FAILED требует расследования; внешнийmailbox не проверен |",
        "| Дополнительные owner PARTIAL | Полный state timeline, global pagination>500, JSON API logs, живой externalTLSfixture |",
        "| Analytics semantics | Sample uptime не равен непрерывнойдоступности; legacy cadence/eligibility не угадываются, gaps неDOWN |",
        "| Accessibility/security |12axe и0known advisories не являются WCAG/production/security сертификацией |",
        "",
        "## 7. Модель и происхождение документации",
        "",
        "Инструмент — OpenAI Codex. Обозначение **solana 6.1 - medium** дано владельцем21октября2026 и воспроизведено буквально. Независимого технического подтверждения modelID или сравнительного исследования моделей нет. Технические имена, API, команды, исходные данные пользователя и кодовые идентификаторы английские; UI и текущие инструкции русские. Подлинные цитаты промптов и raw outputs не переписываются ради языка.",
        "",
        "Архивные отчёты получили русские навигационные редакции со ссылкой на полные исходные документы в immutable Git f3866cd. Это не дословный полный перевод старой прозы и не реконструкция хронологии. Старые artifacts сохранены побайтно; новые имеют ru-prefix.39 исторических записей журнала связаны с исходными строками; metadata исходных файлов в ru-document-provenance.json. Фальшивый session export не создавался.",
        "",
        "## 8. Эссе: черновик, ровно10предложений",
        "",
        "Текст не утверждён владельцем. Счётчик проверяет только тело эссе, без заголовка и этой пометки.",
        "",
    ]
    essay = (
        (ROOT / "docs/essay.md")
        .read_text(encoding="utf-8")
        .split("Сейчас я работаю", 1)[1]
    )
    lines.append("Сейчас я работаю" + essay.strip("\n"))
    lines += ["", "## 9. План до26октября2026", ""]
    roadmap = (ROOT / "docs/roadmap.md").read_text(encoding="utf-8")
    lines.append(roadmap.split("\n", 1)[1])
    lines += [
        "",
        "## 10. Что владелец делает лично",
        "",
        "| Действие | Обязательность | Признак завершения |",
        "|---|---|---|",
        "| Посмотреть русский UI и известные ограничения | P0 | Личное одобрение либо конкретные замечания |",
        "| Прочитать и утвердить10предложений эссе | P0 | Явное согласие с личной формулировкой; правки снова пересчитаны |",
        "| Проверить точную ветку/commit и запустить demo | P0 | Воспроизводится HTTP→incident→Mailpit→recovery→maintenance→public |",
        "| Дать работодателю private read access | P0 | Доступ проверен с аккаунта проверяющего |",
        "| Решить вопрос следующих PR/merge | P1, выбор владельца | Отдельное разрешение на конкретные действия; не обязательный PDF deliverable |",
        "| Передать материалы до26октября | P0, только владелец | Фактическое подтверждение отправки |",
        "| При желании уточнить написание модели в UI | Не блокирует уже честно раскрытое обозначение | При уточнении обновить attribution без догадки о modelID |",
        "",
        "Агент не отправляет письмо работодателю, не выполняет merge, не меняет приватность и не удаляет пользовательские данные. Новая разработка после этой контрольной точки — по следующей команде владельца.",
        "",
    ]
    (ROOT / "docs/OWNER_FINAL_REPORT_RU.md").write_text(
        russian_typography("\n".join(lines)), encoding="utf-8"
    )


if __name__ == "__main__":
    render_owner_report()
