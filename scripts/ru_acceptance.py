"""Recompute Russian acceptance tables from explicit IDs and actual saved test reports."""

import hashlib
import importlib.util
import json
import re
import subprocess
import xml.etree.ElementTree as ET
from collections import Counter
from datetime import UTC, datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
BASE = "f3866cd16a8027855afb4d65c55b598c4d535452"


def read(path):
    return json.loads((ROOT / path).read_text(encoding="utf-8-sig"))


def write(path, data):
    (ROOT / path).write_text(
        json.dumps(data, indent=2, ensure_ascii=False) + "\n", encoding="utf-8"
    )


def russian_typography(text):
    """Space prose without touching code, URLs or immutable quoted prompts."""
    parts = re.split(r"(```[\s\S]*?```|`[^`\n]+`|https?://[^\s)]+)", text)
    fixes = {
        "источникправды": "источник правды",
        "ограниченнаяконкурентность": "ограниченная конкурентность",
        "полныеснимки": "полные снимки",
        "полнаясинхронизация": "полная синхронизация",
        "последовательныеошибки": "последовательные ошибки",
        "Перваяошибка": "Первая ошибка",
        "ложныхинцидентов": "ложных инцидентов",
        "донаблюдений": "до наблюдений",
        "сбрасываеттекущуюметрику": "сбрасывает текущую метрику",
        "историяостаётся": "история остаётся",
        "безфиктивныхнаблюдений": "без фиктивных наблюдений",
        "Логическаядедупликация": "Логическая дедупликация",
        "Реальныйстатус": "Реальный статус",
        "отдельноот": "отдельно от",
        "Остановитьпроверки": "Остановить проверки",
        "Наблюденияпродолжаются": "Наблюдения продолжаются",
        "Быстроевосстановление": "Быстрое восстановление",
        "Отменятьвсюочередьпривосстановлении": "Отменять всю очередь при восстановлении",
        "дляновых": "для новых",
        "неугадывается": "не угадывается",
        "Проверитьтолько": "Проверить только",
        "первый IP": "первый IP",
        "Наблюдаемаядоступность": "Наблюдаемая доступность",
        "Предположить UP междупроверками": "Предположить UP между проверками",
        "загрузитьвсёв": "загрузить всё в",
        "Глобальноотключить": "Глобально отключить",
        "Не меняетсемантику": "Не меняет семантику",
        "Единыйчёрно-белый": "Единый чёрно-белый",
        "Компактныйлокальныйпродукт": "Компактный локальный продукт",
        "Русскийязык": "Русский язык",
        "Локализоватьпредставление": "Локализовать представление",
        "Одинязыкбеззависимостей": "Один язык без зависимостей",
        "Историядоказательств": "История доказательств",
        "Русскаяредакцияархивовсоссылкойна": "Русская редакция архивов со ссылкой на",
        "исходныепромптыи": "исходные промпты и",
        "нетронуты": "не тронуты",
        "Переписатьпрошлыесобытия": "Переписать прошлые события",
        "объявитьстарыйтестновым": "объявить старый тест новым",
        "Историяпроверяема": "История проверяема",
        "новыеотчётынесутсвоифактическиевремя": "новые отчёты несут свои фактические время",
        "окончательнаяотправка": "окончательная отправка",
        "раннихотчётах": "ранних отчётах",
        "исполнениятестов": "исполнения тестов",
        "финальнуюпроверку": "финальную проверку",
        "русскомэтапе": "русском этапе",
        "существующейрегрессии": "существующей регрессии",
        "черновикаэссе": "черновика эссе",
        "русскимподписям": "русским подписям",
        "личногоутверждения": "личного утверждения",
        "непрерывнойдоступности": "непрерывной доступности",
        "владельцем21": "владельцем 21",
        "толькоотдельный": "только отдельный",
        "Фактическиепроверки": "Фактические проверки",
    }
    for index in range(0, len(parts), 2):
        for old, new in fixes.items():
            parts[index] = parts[index].replace(old, new)
        parts[index] = re.sub(
            r"(?<=[А-Яа-яЁё])(?=[A-Za-z0-9])|(?<=[A-Za-z0-9])(?=[А-Яа-яЁё])",
            " ",
            parts[index],
        )
        parts[index] = re.sub(r"(?<=[А-Яа-яЁё]):(?=[А-Яа-яЁё])", ": ", parts[index])
    return "".join(parts)


def git(*args):
    return subprocess.check_output(
        ["git", *args], cwd=ROOT, text=True, encoding="utf-8"
    ).strip()


def verify_sources():
    immutable = [
        "backend/app/worker.py",
        "backend/app/analytics.py",
        "backend/app/security.py",
        "backend/app/models.py",
        "backend/app/notifications.py",
        "backend/migrations",
        "compose.yaml",
        ".env.example",
    ]
    assert not git("diff", BASE, "--name-only", "--", *immutable)
    subprocess.run(
        ["git", "merge-base", "--is-ancestor", BASE, "HEAD"], cwd=ROOT, check=True
    )
    hits = []
    patterns = [
        r"-----BEGIN (?:RSA |EC |OPENSSH )?PRIVATE KEY-----",
        r"gh[pousr]_" + r"[A-Za-z0-9]{30,}",
        r"AKIA" + r"[A-Z0-9]{16}",
    ]
    for name in git("ls-files").splitlines():
        path = ROOT / name
        if not path.is_file() or path.stat().st_size > 2_000_000:
            continue
        try:
            text = path.read_text(encoding="utf-8")
        except UnicodeError:
            continue
        if any(re.search(pattern, text) for pattern in patterns):
            hits.append(name)
    assert not hits
    assert ".env" not in git("ls-files").splitlines()
    write(
        "artifacts/ru-source-review.json",
        {
            "checked_at": datetime.now(UTC).isoformat(),
            "status": "PASS",
            "head": git("rev-parse", "HEAD"),
            "unchanged_monitoring_policy_paths": immutable,
            "limited_secret_pattern_hits": hits,
            "limits": "Finite current tracked-text patterns, not universal secret detection; complete past history scan retained in phase7-git-review.json.",
        },
    )


def verify_prior_performance():
    spec = importlib.util.spec_from_file_location(
        "prior_acceptance", ROOT / "scripts/phase7_acceptance_audit.py"
    )
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    module.write = lambda _path, data: write(
        "artifacts/ru-performance-reference.json", data
    )
    result = module.verify_prior_performance()
    assert result["steady"]["starts"] == 475 and result["fault"]["starts"] == 295
    return result


def validate_documents():
    required = [
        "README.md",
        "docs/architecture.md",
        "docs/decisions.md",
        "docs/ai-development.md",
        "docs/demo-script.md",
        "docs/submission-guide.md",
        "docs/roadmap.md",
        "docs/release-checklist.md",
        "docs/development-log.md",
        "docs/progress.md",
    ]
    hashes = {}
    for name in required:
        text = (ROOT / name).read_text(encoding="utf-8")
        assert re.search(r"[А-Яа-яЁё]", text), name
        for link in re.findall(r"\]\(([^)]+)\)", text):
            if not link.startswith(("https:", "http:", "#", "codex:")):
                assert ((ROOT / name).parent / link.split("#")[0]).exists(), (
                    name,
                    link,
                )
        hashes[name] = hashlib.sha256(text.encode()).hexdigest()
    essay = (
        (ROOT / "docs/essay.md")
        .read_text(encoding="utf-8")
        .split("Сейчас я работаю", 1)[1]
    )
    essay = "Сейчас я работаю" + essay
    sentences = re.findall(r"[^.!?]+[.!?]", essay)
    assert len(sentences) == 10 and all(s.strip() for s in sentences)
    model = (ROOT / "docs/ai-development.md").read_text(encoding="utf-8")
    assert (
        "gpt-6.1-sol" in model
        and "model-session-metadata.json" in model
        and "24 записи" in model
    )
    write(
        "artifacts/ru-document-review.json",
        {
            "checked_at": datetime.now(UTC).isoformat(),
            "status": "PASS",
            "reviewed_hashes": hashes,
            "essay_sentences": len(sentences),
            "essay_approved_by_owner": False,
            "model_source": "native primary-session turn_context metadata; docs/model-session-metadata.json; 24 medium, 2 high",
            "historical_sources": "f3866cd immutable Git; prompts retain actual wording; old raw artifacts not relabeled",
        },
    )


def ids(prefix, start, end=None):
    return [f"{prefix}-{i:02}" for i in range(start, (end or start) + 1)]


SECTIONS = {
    "Backend": [
        "GEN-01",
        "GEN-02",
        "FND-04",
        "FND-05",
        "MON-10",
        *ids("GRP", 1, 4),
        "INC-04",
        "INC-05",
    ],
    "Frontend": ["GEN-03", *ids("UI", 1, 13), "PUB-01", "PUB-02", "SCN-01", "SCN-02"],
    "PostgreSQL": ["GEN-04", "FND-01", "FND-02", "REL-05", "INC-03", "P4-21", "P5-02"],
    "Мониторинг": [
        *ids("MON", 1, 9),
        "FND-03",
        *ids("SCN", 6, 8),
        *ids("SCN", 12, 14),
        "SCN-17",
        "SCN-18",
        *ids("REL", 1, 3),
    ],
    "Уведомления": [
        *ids("NTF", 1, 8),
        *ids("MNT", 1, 8),
        *ids("SCN", 3, 5),
        *ids("SCN", 9, 11),
        "P6-REQ-02",
    ],
    "Аналитика": [*ids("HIS", 1, 9), *ids("P5", 9, 11), "P6-REQ-04", "P6-REQ-07"],
    "Безопасность": [
        *ids("SEC", 1, 10),
        "PUB-03",
        "PUB-04",
        "SCN-16",
        "P5-05",
        "P5-06",
        "P5-08",
    ],
    "Тестирование": [
        "DEL-04",
        "DEL-05",
        *ids("P7", 7, 12),
        "P4-19",
        "P5-15",
        "P6-REQ-12",
        "P7-24",
    ],
    "GitHub": [
        "DEL-16",
        "DEL-17",
        "DEL-18",
        "P4-23",
        "P4-24",
        "P5-01",
        "P7-22",
        "P7-23",
        "P7-24",
    ],
    "Документация": [
        "GEN-06",
        "GEN-07",
        "GEN-08",
        "GEN-12",
        "DEL-09",
        *ids("DEL", 10, 15),
        *ids("DEL", 19, 22),
        "P7-20",
        *ids("P7", 25, 30),
    ],
}


def counts(rows):
    c = Counter(row["status"] for row in rows)
    denominator = sum(c[s] for s in ["PASS", "PARTIAL", "FAIL", "NOT VERIFIED"])
    return {
        "counts": dict(c),
        "denominator": denominator,
        "percent": round(100 * c["PASS"] / denominator, 2) if denominator else None,
    }


def evidence_gate():
    xml = ET.parse(ROOT / "artifacts/ru-backend-tests.xml")
    assert len(list(xml.iter("testcase"))) == 150
    assert not any(list(xml.iter(tag)) for tag in ["failure", "error", "skipped"])
    unit = read("artifacts/ru-component-tests.json")
    assert (
        unit["numPassedTests"] == 35
        and unit["numFailedTests"] == unit["numPendingTests"] == 0
    )
    browser = read("artifacts/ru-browser-tests.json")["stats"]
    assert browser["expected"] == 12 and all(
        browser[k] == 0 for k in ["unexpected", "flaky", "skipped"]
    )
    for name in [
        "ru-ui-audit",
        "ru-smtp-faults",
        "ru-clean-checkout",
        "ru-email-continuation",
    ]:
        assert read("artifacts/" + name + ".json")["status"] == "PASS", name
    assert len(read("artifacts/ru-smtp-faults.json")["checks"]) == 7
    axe = [
        scan
        for width in [390, 768, 1440, 1920]
        for scan in read(f"artifacts/ru-accessibility-{width}.json")
    ]
    assert len(axe) == 12 and all(not s["violations"] for s in axe)
    assert (
        read("artifacts/ru-npm-audit.json")["metadata"]["vulnerabilities"]["total"] == 0
    )
    assert all(
        not package["vulns"]
        for package in read("artifacts/ru-pip-audit.json")["dependencies"]
    )
    return {
        "backend": 150,
        "component": 35,
        "browser": 12,
        "axe_scans": 12,
        "axe_violations": 0,
        "browser_stats": browser,
    }


def render():
    gate = evidence_gate()
    data = read("docs/phase7-criteria.json")
    rows = data["rows"]
    assert len(rows) == len({r["id"] for r in rows}) == 232
    by_id = {r["id"]: r for r in rows}
    ci_path = ROOT / "artifacts/ru-ci.json"
    ci = read("artifacts/ru-ci.json") if ci_path.exists() else None
    if ci:
        assert ci["conclusion"] == "success" and len(ci["jobs"]) == 3
        assert all(j["conclusion"] == "success" for j in ci["jobs"])
        assert ci["downloaded_browser_evidence"]["expected"] == 12
    for identity in ["DEL-06", "DEL-07", "P7-24"]:
        by_id[identity]["status"] = "PASS" if ci else "NOT VERIFIED"
    substitutions = {
        "phase7-backend-tests.xml": "ru-backend-tests.xml",
        "phase7-frontend-tests.json": "ru-component-tests.json",
        "phase7-browser-tests.json": "ru-browser-tests.json",
        "phase7-clean-checkout.json": "ru-clean-checkout.json",
        "phase7-smtp-faults.json": "ru-smtp-faults.json",
        "phase7-email-continuation.json": "ru-email-continuation.json",
        "phase7-performance-review.json": "ru-performance-reference.json",
        "phase7-document-review.json": "ru-document-review.json",
        "phase7-git-review.json": "ru-source-review.json",
        "phase7-ci.json": "ru-ci.json",
    }
    for row in rows:
        row.setdefault("phase7_original_test_result", row["test_result"])
        row["evidence"] = [
            "artifacts/" + substitutions[Path(p).name]
            if Path(p).name in substitutions
            else p
            for p in row["evidence"]
        ]
        row["test"] = [
            p.replace(
                "scripts/phase7_acceptance_audit.py::verify_git_contract",
                "scripts/ru_acceptance.py::verify_sources",
            )
            .replace(
                "scripts/phase7_acceptance_audit.py::validate_documents",
                "scripts/ru_acceptance.py::validate_documents",
            )
            .replace(
                "scripts/phase7_acceptance_audit.py::verify_prior_performance",
                "scripts/ru_acceptance.py::verify_prior_performance",
            )
            for p in row["test"]
        ]
        for name in row["implementation"]:
            assert (ROOT / name).exists(), (row["id"], name)
        for name in row["evidence"]:
            assert (ROOT / name).exists() or row["status"] == "NOT VERIFIED", (
                row["id"],
                name,
            )
        row["test_result"] = (
            "См. фактический результат конкретного теста и границы ниже; исходный Phase7-результат сохранён отдельно."
        )
        if row["status"] in {"PARTIAL", "NOT VERIFIED"}:
            row["test_result"] = row["status"] + ": " + row["limitation_ru"]
    write("docs/phase7-criteria.json", data)
    summaries = {
        origin: counts([r for r in rows if r["origin"] == origin])
        for origin in ["M", "O", "T", "OPT"]
    }
    sections = {
        name: {"ids": identities, **counts([by_id[i] for i in identities])}
        for name, identities in SECTIONS.items()
    }
    write(
        "artifacts/ru-readiness.json",
        {
            "checked_at": datetime.now(UTC).isoformat(),
            "formula": "PASS/(PASS+PARTIAL+FAIL+NOT VERIFIED)*100",
            "origins": summaries,
            "mandatory_project": counts([r for r in rows if r["origin"] != "OPT"]),
            "sections": sections,
            "gate": gate,
            "sections_overlap": True,
            "note": "Section IDs are explicit overlapping lenses, never summed into employer readiness;232 original criteria retained.",
        },
    )
    lines = [
        "# Текущая русская матрица приёмки",
        "",
        "Дата редакции:21октября2026.232 связанных проектных критерия, не232 независимых требования работодателя. M/O/T/OPT разделены; PARTIAL не получает полного балла. Машинная provenance: phase7-criteria.json, русские поля *_ru. Старые нагрузочные измерения20октября помечены отдельно, свежие regression artifacts имеют префиксru-.",
        "",
        "| ID / источник / приоритет | Критерий и приёмка | Реализация | Конкретная проверка | Результат и доказательство | Статус / ограничение |",
        "|---|---|---|---|---|---|",
    ]

    def safe(value):
        return value.replace("|", "\\|").replace("\n", " ")

    for r in rows:
        columns = [
            f"{r['id']} / {r['origin']} / {r['priority']}",
            r["requirement_ru"] + "; " + r["acceptance_ru"],
            "; ".join(r["implementation"]),
            "; ".join(r["test"]),
            r["test_result"] + "; " + "; ".join(r["evidence"]),
            r["status"] + ": " + r["limitation_ru"],
        ]
        lines.append("| " + " | ".join(safe(c) for c in columns) + " |")
    (ROOT / "docs/phase7-final-acceptance.md").write_text(
        russian_typography("\n".join(lines) + "\n"), encoding="utf-8"
    )
    return summaries, sections


if __name__ == "__main__":
    assert (
        counts([{"status": s} for s in ["PASS", "PARTIAL", "NOT APPLICABLE"]])[
            "percent"
        ]
        == 50
    )
    verify_sources()
    verify_prior_performance()
    validate_documents()
    summary, _sections = render()
    print(json.dumps(summary, indent=2, ensure_ascii=False))
