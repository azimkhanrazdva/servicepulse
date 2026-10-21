# Контрольная точка Phase3: инциденты

Русская навигационная редакция подготовлена 21 октября 2026. Это архив: даты, результаты и незавершённые пункты относятся к описанному этапу. Полный исходный отчёт сохранён в [Git](https://github.com/azimkhanrazdva/servicepulse/blob/f3866cd16a8027855afb4d65c55b598c4d535452/docs/phase3-checkpoint.md); настоящий перевод не является новым выполнением команд.

Добавлены threshold confirmation, unique открытый incident, recovery и отдельные PAUSED/CONFIG_CHANGED, журнал с фильтрами/pagination, ticking duration и два SSE-клиента. Миграция 0003 не создаёт вымышленных старых инцидентов. Проверки:75 backend,11 component,4 browser PASS15,2 с; smoke73,031 с. HIGH: nginx сохранял старый backendIP после замены, три browser-сценария падали; исправлено обновлением DockerDNS каждые 2 с, deterministic different-IP smoke4,563 с. Ни один тест не удалялся. SMTP/public/monthly/load тогда оставались следующими этапами.
