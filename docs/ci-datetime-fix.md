# Исправление CI и открытие репозитория — 21 октября 2026

Это дополнение отражает состояние после русской контрольной точки `7dae3d2`. Оно имеет приоритет над прежними упоминаниями приватности и оценки доступа. Старые успешные прогоны не отменяют последующий FAIL.

| Проверка | Факт / состояние |
|---|---|
| Упавший PR-прогон | [39562658442](https://github.com/azimkhanrazdva/servicepulse/actions/runs/39562658442), PR #4, head `7dae3d230b3e38527e78ad6dc117a451605ff4f6`: 11 browser PASS, 1 FAIL |
| Причина | `maintenance.spec.ts`: `fill("2026-10-21T07:35:00")` → `Malformed value`; Chromium нормализует значение в `2026-10-21T07:35`, Playwright отвергает несовпадение |
| Воспроизведение | Настоящий Chromium, фиксированное значение, исходная ошибка воспроизведена; `artifacts/ci-datetime-reproduction.json` |
| Исправление | Общий `frontend/e2e/datetime.ts` удаляет только завершающие нулевые секунды; оба вызывающих теста maintenance/release используют его. Ненулевые секунды и timezone conversion сохранены |
| Детерминированная проверка | Новый browser test: секунды 00/01/59 и полночь, native validity и точное значение; 10 повторов PASS, `ci-datetime-regression.json` |
| Полная локальная регрессия | 13 Chromium PASS, 0 skipped/flaky/unexpected; 35 component PASS; typecheck, ESLint, Prettier и build PASS. Backend локально заново не запускался: production code не менялся |
| Текущий hosted CI | Исправление `76e675516054680fb6145b947b3ae22b207d7d09`: [push 39567089094](https://github.com/azimkhanrazdva/servicepulse/actions/runs/39567089094) и [PR 39567096370](https://github.com/azimkhanrazdva/servicepulse/actions/runs/39567096370) SUCCESS, во всех 3 jobs. Оба скачанных browser artifacts: 13 PASS, 0 skipped/flaky/unexpected, 12 axe scans без нарушений. JSON: `ci-datetime-push.json`, `ci-datetime-pr.json` |
| Публикация | После прямой команды владельца «сделай репозиторий публичным» выполнен обычный `gh repo edit --visibility public --accept-visibility-change-consequences`; GitHub подтвердил `isPrivate=false` |
| Проверка перед публикацией | 699 текстовых blobs доступной истории и текущие tracked files, выбранные шаблоны ключей/токенов без совпадений; `.env` не отслеживается. Это ограниченный scan, не универсальная гарантия отсутствия секретов |
| Доступ работодателя | Без авторизации получен HTTP 200 для репозитория, актуальной ветки и commit `7dae3d2`. Приглашение теперь не нужно; это подтверждение технической доступности, не прочтения материалов работодателем |

## Правильная ссылка

- [Актуальная ветка codex/russian-submission](https://github.com/azimkhanrazdva/servicepulse/tree/codex/russian-submission).
- [Снимок 7dae3d2 до исправления CI](https://github.com/azimkhanrazdva/servicepulse/commit/7dae3d230b3e38527e78ad6dc117a451605ff4f6).
- [Проверенное исправление 76e6755](https://github.com/azimkhanrazdva/servicepulse/commit/76e675516054680fb6145b947b3ae22b207d7d09).
- [Существующий PR #4](https://github.com/azimkhanrazdva/servicepulse/pull/4).

В `main` остаётся неполная версия 0.1; для проверки использовать указанную ветку и новый commit исправления. Merge не выполнялся. Письмо работодателю не отправлялось, данные и volumes не удалялись. Эссе по-прежнему требует личного утверждения владельца.

Таблицы предыдущего отчёта ниже относятся к контрольной точке до обнаружения нестабильности и открытия репозитория. Старый PARTIAL доступа не описывает новое публичное состояние; итоговый acceptance audit после этих изменений отдельно не пересчитывался.

Следующий документальный commit получает собственную проверку push/PR Actions; snapshot выше относится именно к исправлению `76e6755`. Run итогового HEAD указывается в ответе владельцу без бесконечного цикла commit→proof→commit. Прежний упавший прогон сохранён как FAIL, а не перезаписан успешным rerun.
