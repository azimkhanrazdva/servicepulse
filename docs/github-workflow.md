# GitHub: фактическая история и безопасный порядок действий

Репозиторий https://github.com/azimkhanrazdva/servicepulse открыт по явной команде владельца 21 октября 2026; до этого был приватным. Без авторизации проверены HTTP 200 репозитория, ветки и снимка. Main хранит раннюю 0.1; актуальный код — `codex/russian-submission`. История не переписывается; обычный push разрешён после проверки. Новые PR, merge, release/tag и последующая смена видимости требуют отдельного решения.

## Существующая цепочка

| Этап | Head | Base | Фактический PR |
|---|---|---|---|
| Phase2 | feat/monitor-management-groups | main |#1 |
| Phase3 | feat/incident-lifecycle | feat/monitor-management-groups |#2 |
| Phase4 | feat/maintenance-email-outbox | feat/incident-lifecycle |#3 |
| Phase5 | feat/public-status-analytics | feat/maintenance-email-outbox | Только подготовлен текст |
| Phase6 | feat/reliability-audit-redesign | feat/public-status-analytics | Только подготовлен текст |
| Phase7 | feat/final-acceptance-release | feat/reliability-audit-redesign | Только подготовлен текст |
| Русская версия, сводный PR | codex/russian-submission | main | [#4](https://github.com/azimkhanrazdva/servicepulse/pull/4), уже существовал при исправлении CI; содержит накопленные этапы |

PR#1/#2/#3 были созданы по последующему явному запросу владельца; это не подтверждение review в прошлом. Проверка 20 октября: OPEN/MERGEABLE/CLEAN, корректные ancestorbases, CI успешен, formalreviews0, heads3569b1c/3529b66/442496f. Новые действительные состояния фиксируются в текущем отчёте; старые проверки не заменяют свежие. Поздние Phase6 исправления не приписываются старым Phase4heads.

## Подготовленные команды, не свидетельство исполнения

После отдельного разрешения владельца:

```powershell
gh pr create --repo azimkhanrazdva/servicepulse --head feat/public-status-analytics --base feat/maintenance-email-outbox --title 'feat: add isolated public status and observed analytics' --body-file docs/pr-phase5.md
gh pr create --repo azimkhanrazdva/servicepulse --head feat/reliability-audit-redesign --base feat/public-status-analytics --title 'feat: verify reliability and refine monitoring interface' --body-file docs/pr-phase6.md
gh pr create --repo azimkhanrazdva/servicepulse --head feat/final-acceptance-release --base feat/reliability-audit-redesign --title 'test: complete final acceptance' --body-file docs/pr-phase7.md
```

Для русского этапа headcodex/russian-submission/basefeat/final-acceptance-release; текст отчёта сам по себе не разрешает PR. Номера будущих PR не выдумываются. При разрешённом merge идти Phase2→3→4→5→6→7→RU, предпочитать mergecommits, после вливания очередной базы менять следующий base на main и перепроверять diff/checks. Например `gh pr merge 1 --merge`, затем `gh pr edit 2 --base main` допустимы только после разрешения. Не squash/rebase общую цепочку, не force-push, не удалять basebranch пока есть dependents.

Перед передачей дать работодателю точную ссылку на проверенную ветку/commit либо закончить разрешённую цепочку. Создание PR не отдельное обязательное требование MadDevs; это выбранное владельцем подтверждение GitHubFlow. Подробные исходные команды/CI истории доступны в Git:f3866cd и rawartifacts.
