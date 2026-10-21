import { reasonLabel, sectionLabel } from "./ru";
import { statusLabel } from "./ru";
import { useEffect, useState } from "react";
import { request } from "./api";
import type { Monitor, Group } from "./api";
import { MonitorForm } from "./MonitorForm";
import { GroupsPanel } from "./GroupsPanel";
import { IncidentsPanel } from "./IncidentsPanel";
import { MaintenancePanel } from "./MaintenancePanel";
import type { MaintenanceSnapshot } from "./MaintenancePanel";
import { AnalyticsPanel } from "./AnalyticsPanel";
import { PublicationPanel } from "./PublicationPanel";
import { OutageDuration } from "./OutageDuration";
import { Modal } from "./Modal";
import { NotificationsPanel } from "./NotificationsPanel";

type Result = {
  id: string;
  checked_at: string;
  success: boolean;
  status_code: number | null;
  response_ms: number;
  error: string | null;
};

export function App() {
  const [activeSection, setActiveSection] = useState(
    location.hash.slice(1) || "overview",
  );
  const [menuOpen, setMenuOpen] = useState(false);
  const [lastUpdate, setLastUpdate] = useState<string | null>(null);
  const [search, setSearch] = useState("");
  const [statusFilter, setStatusFilter] = useState("");
  const [sort, setSort] = useState("name");
  useEffect(() => {
    const changed = () => {
      setActiveSection(location.hash.slice(1) || "overview");
      setMenuOpen(false);
    };
    window.addEventListener("hashchange", changed);
    return () => window.removeEventListener("hashchange", changed);
  }, []);
  const [overview, setOverview] = useState<{
    active_incidents: number;
    opened_at: Record<string, string>;
  } | null>(null);
  const [uptime, setUptime] = useState<
    Record<string, { samples: number; percent: number }>
  >({});
  const [overviewError, setOverviewError] = useState("");
  const [monitors, setMonitors] = useState<Monitor[]>([]);
  const [loading, setLoading] = useState(true);
  const [connection, setConnection] = useState("Подключение");
  const [error, setError] = useState("");
  const [form, setForm] = useState(false);
  const [formBusy, setFormBusy] = useState(false);
  const [busy, setBusy] = useState(false);
  const [editing, setEditing] = useState<Monitor | undefined>();
  const [groups, setGroups] = useState<Group[]>([]);
  const [groupFilter, setGroupFilter] = useState<string | null>(null);
  const [notice, setNotice] = useState("");
  const [selected, setSelected] = useState<Monitor | null>(null);
  const [results, setResults] = useState<Result[]>([]);
  const [historyLoading, setHistoryLoading] = useState(false);
  const [incidentRevision, setIncidentRevision] = useState(0);
  const [maintenanceRevision, setMaintenanceRevision] = useState(0);
  const [maintenance, setMaintenance] = useState<MaintenanceSnapshot>({
    items: [],
    has_more: false,
    active_monitor_ids: [],
    active_group_ids: [],
  });

  useEffect(() => {
    let active = true;
    const load = () =>
      request<{
        active_incidents: number;
        opened_at: Record<string, string>;
        uptime_24h: Record<string, { samples: number; percent: number }>;
      }>("/overview")
        .then((data) => {
          if (active) {
            setOverview((previous) => previous ?? data);
            setUptime(data.uptime_24h ?? {});
            setOverviewError("");
          }
        })
        .catch((e) => {
          if (active) {
            setUptime({});
            setOverviewError(e.message);
          }
        });
    void load();
    window.addEventListener("online", load);
    const timer = setInterval(load, 30000);
    return () => {
      active = false;
      clearInterval(timer);
      window.removeEventListener("online", load);
    };
  }, []);

  useEffect(() => {
    let active = true;
    let receivedSnapshot = false;
    let receivedGroups = false;
    request<Group[]>("/groups")
      .then((data) => {
        if (active && !receivedGroups) setGroups(data);
      })
      .catch((e) => {
        if (active) setError(e.message);
      });
    request<Monitor[]>("/monitors")
      .then((data) => {
        if (active && !receivedSnapshot) setMonitors(data);
      })
      .catch((e) => {
        if (active) setError(e.message);
      })
      .finally(() => {
        if (active) setLoading(false);
      });
    let events: EventSource;
    const connect = () => {
      events?.close();
      events = new EventSource("/api/events");
      events.addEventListener("maintenance", (event) => {
        try {
          setMaintenance(JSON.parse((event as MessageEvent).data));
          setMaintenanceRevision((v) => v + 1);
        } catch {
          setError("Не удалось прочитать обновление обслуживания.");
        }
      });
      events.addEventListener("overview", (event) => {
        try {
          setOverview(JSON.parse((event as MessageEvent).data));
        } catch {
          setOverviewError("Не удалось прочитать сводку инцидентов.");
        }
      });
      events.addEventListener("incidents", () =>
        setIncidentRevision((value) => value + 1),
      );
      events.addEventListener("groups", (event) => {
        try {
          receivedGroups = true;
          setGroups(JSON.parse((event as MessageEvent).data));
        } catch {
          setError("Не удалось прочитать обновление групп.");
        }
      });
      events.onopen = () => setConnection("На связи");
      events.onmessage = (event) => {
        try {
          receivedSnapshot = true;
          setMonitors(JSON.parse(event.data));
          setLastUpdate(new Date().toISOString());
          setLoading(false);
          setConnection("На связи");
        } catch {
          setConnection("Некорректное обновление");
        }
      };
      events.onerror = () => setConnection("Переподключение");
    };
    const offline = () => {
      events?.close();
      setConnection("Переподключение");
    };
    connect();
    window.addEventListener("offline", offline);
    window.addEventListener("online", connect);
    return () => {
      active = false;
      events.close();
      window.removeEventListener("offline", offline);
      window.removeEventListener("online", connect);
    };
  }, []);

  const selectedId = selected?.id;
  const selectedCheck = monitors.find(
    (m) => m.id === selectedId,
  )?.last_checked_at;
  useEffect(() => {
    if (!selectedId) return;
    let active = true;
    setHistoryLoading(true);
    request<Result[]>(`/monitors/${selectedId}/results`)
      .then((data) => {
        if (active) setResults(data);
      })
      .catch((e) => {
        if (active) setError(e.message);
      })
      .finally(() => {
        if (active) setHistoryLoading(false);
      });
    return () => {
      active = false;
    };
  }, [selectedId, selectedCheck]);

  async function action(
    monitor: Monitor,
    operation: "run" | "pause" | "resume" | "delete",
  ) {
    if (
      operation === "delete" &&
      !window.confirm(
        `Удалить монитор «${monitor.name}» и историю его наблюдений?`,
      )
    )
      return;
    setBusy(true);
    setError("");
    setNotice("");
    try {
      if (operation === "delete") {
        await request(
          `/monitors/${monitor.id}?config_version=${monitor.config_version}`,
          { method: "DELETE" },
        );
        setMonitors((previous) => previous.filter((m) => m.id !== monitor.id));
        if (selected?.id === monitor.id) setSelected(null);
      } else if (operation === "run") {
        await request(`/monitors/${monitor.id}/run`, { method: "POST" });
      } else {
        const updated = await request<Monitor>(
          `/monitors/${monitor.id}/${operation}`,
          {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({ config_version: monitor.config_version }),
          },
        );
        setMonitors((previous) =>
          previous.map((m) => (m.id === updated.id ? updated : m)),
        );
      }
      setNotice(
        operation === "run"
          ? "Проверка поставлена в очередь."
          : operation === "delete"
            ? "Монитор удалён."
            : operation === "pause"
              ? "Монитор приостановлен."
              : "Монитор возобновлён.",
      );
    } catch (e) {
      setError((e as Error).message);
    } finally {
      setBusy(false);
    }
  }
  function saved(monitor: Monitor) {
    setMonitors((previous) => [
      ...previous.filter((m) => m.id !== monitor.id),
      monitor,
    ]);
    setForm(false);
    setEditing(undefined);
    setGroupFilter(null);
    setNotice("Монитор сохранён.");
  }
  function groupChanged(value: Group | string) {
    setGroups((previous) =>
      typeof value === "string"
        ? previous.filter((g) => g.id !== value)
        : [...previous.filter((g) => g.id !== value.id), value],
    );
    if (typeof value === "string" && groupFilter === value)
      setGroupFilter(null);
  }

  const counts = ["UP", "DOWN", "UNKNOWN", "PAUSED"].map(
    (state) => monitors.filter((m) => m.state === state).length,
  );
  const current = monitors.find((m) => m.id === selected?.id);
  const filteredGroup = groups.find((g) => g.id === groupFilter);
  const grouped = filteredGroup
    ? monitors.filter((m) => filteredGroup.monitor_ids.includes(m.id))
    : monitors;
  const visible = grouped
    .filter(
      (m) =>
        (!statusFilter || m.state === statusFilter) &&
        `${m.name} ${m.url}`.toLowerCase().includes(search.toLowerCase()),
    )
    .sort((a, b) =>
      sort === "latency"
        ? (b.last_response_ms ?? -1) - (a.last_response_ms ?? -1)
        : sort === "status"
          ? a.state.localeCompare(b.state) || a.name.localeCompare(b.name)
          : a.name.localeCompare(b.name),
    );
  const samples = Object.values(uptime);
  const totalSamples = samples.reduce((sum, s) => sum + s.samples, 0);
  const observed = totalSamples
    ? samples.reduce((sum, s) => sum + s.samples * s.percent, 0) / totalSamples
    : null;
  const responses = monitors.filter(
    (m) => m.last_response_ms !== null && m.state !== "PAUSED",
  );
  const average = responses.length
    ? responses.reduce((sum, m) => sum + (m.last_response_ms ?? 0), 0) /
      responses.length
    : null;
  return (
    <div className="shell">
      <a className="skip-link" href="#overview">
        Перейти к основному содержимому
      </a>
      <aside
        className={menuOpen ? "menu-open" : ""}
        onKeyDown={(e) => {
          if (e.key === "Escape") {
            setMenuOpen(false);
            e.currentTarget
              .querySelector<HTMLButtonElement>(".menu-toggle")
              ?.focus();
          }
        }}
      >
        <a className="brand" href="#overview">
          <span className="brand-icon">ϟ</span> ServicePulse
        </a>
        <button
          className="menu-toggle"
          aria-expanded={menuOpen}
          aria-controls="workspace-nav"
          onClick={() => setMenuOpen(!menuOpen)}
        >
          Меню разделов {menuOpen ? "−" : "+"}
        </button>
        <div className="workspace">
          РАБОЧАЯ ОБЛАСТЬ <span>ЛОКАЛЬНО</span>
        </div>
        <nav id="workspace-nav" aria-label="Основная навигация">
          {[
            ["overview", "◉", "Обзор"],
            ["monitors", "▤", "Все мониторы"],
            ["groups", "◇", "Группы"],
            ["incidents", "!", "Журнал инцидентов"],
            ["maintenance", "◷", "Обслуживание"],
            ["notifications", "✉", "Уведомления"],
            ["publication", "↗", "Публичные страницы"],
          ].map(([id, icon, label]) => (
            <a
              key={id}
              href={`#${id}`}
              aria-current={activeSection === id ? "page" : undefined}
              className={activeSection === id ? "active" : ""}
            >
              <span aria-hidden="true" className="nav-icon">
                {icon}
              </span>
              <span>{label}</span>
            </a>
          ))}
        </nav>
        <div className="sidebar-note">
          <span className="tag">ЛОКАЛЬНОЕ ОКРУЖЕНИЕ</span>
          <p>
            Ваши сервисы.
            <br />
            Их реальное состояние.
          </p>
          <small>Локальное управление · реальные наблюдения</small>
        </div>
        <footer>
          <a href="/api/health" target="_blank" rel="noreferrer">
            Состояние системы ↗
          </a>
          <a href="http://localhost:8000/docs" target="_blank" rel="noreferrer">
            Документация API ↗
          </a>
          <span>ServicePulse v1.0</span>
        </footer>
      </aside>
      <main id="overview" tabIndex={-1}>
        <header>
          <span>
            Рабочая область <b>/</b> {sectionLabel(activeSection)}
          </span>
          <span
            className={`connection ${connection === "На связи" ? "live" : ""}`}
            role="status"
          >
            ● {connection}
          </span>
        </header>
        <div className="page-title">
          <div>
            <div className="eyebrow">МОНИТОРИНГ / ОБЗОР</div>
            <h1>
              Обзор<span className="title-dot">.</span>
            </h1>
            <p>Доступность сервисов, инциденты и результаты проверок.</p>
            <small className="last-update">
              Обновлено:{" "}
              {lastUpdate
                ? new Date(lastUpdate).toLocaleTimeString("ru-RU")
                : "Ожидание данных"}
            </small>
          </div>
          <button
            className="primary"
            onClick={() => {
              setEditing(undefined);
              setForm(!form);
            }}
          >
            {form ? "Закрыть форму" : "+ Добавить монитор"}
          </button>
        </div>
        {error && (
          <div className="error" role="alert">
            {error}
            <button
              onClick={() => setError("")}
              aria-label="Закрыть сообщение об ошибке"
            >
              ×
            </button>
          </div>
        )}
        {notice && (
          <div className="notice" aria-live="polite">
            {notice}
            <button
              aria-label="Закрыть подтверждение"
              onClick={() => setNotice("")}
            >
              ×
            </button>
          </div>
        )}
        {form && (
          <Modal
            busy={formBusy}
            onClose={() => {
              setForm(false);
              setEditing(undefined);
            }}
          >
            <MonitorForm
              key={editing?.id ?? "new"}
              initial={editing}
              onSaved={saved}
              onBusyChange={setFormBusy}
              onCancel={() => {
                setForm(false);
                setEditing(undefined);
              }}
            />
          </Modal>
        )}
        <section className="stats" aria-label="Сводка мониторов">
          {[
            [
              "Всего мониторов",
              monitors.length,
              "Загруженная выборка · не более 500",
            ],
            ["Доступны", counts[0], "Подтверждённая доступность в выборке"],
            ["Недоступны", counts[1], "Порог ошибок достигнут"],
            [
              "На паузе",
              monitors.filter((m) => m.state === "PAUSED").length,
              "Загруженная выборка",
            ],
            [
              "Ожидание данных",
              monitors.filter((m) => m.state === "UNKNOWN").length,
              "Загруженная выборка",
            ],
            [
              "Активные инциденты",
              overview?.active_incidents ?? "—",
              "Все сохранённые открытые инциденты",
            ],
            [
              "Доступность по проверкам · 24 ч",
              observed === null ? "НЕТ ДАННЫХ" : `${observed.toFixed(2)}%`,
              "По числу проверок · загруженная выборка",
            ],
            [
              "Среднее время ответа",
              average === null ? "НЕТ ДАННЫХ" : `${Math.round(average)} мс`,
              "Последние активные наблюдения · выборка",
            ],
          ].map(([label, value, hint]) => (
            <article key={label}>
              <span>{label}</span>
              <strong>{value}</strong>
              <small>{hint}</small>
            </article>
          ))}
        </section>
        {overviewError && (
          <p className="error" role="alert">
            Аналитика сводки: {overviewError}
          </p>
        )}
        <section className="panel" id="monitors">
          <div className="section-heading">
            <div>
              <h2>
                Мониторы сервисов <span>{visible.length}</span>
              </h2>
              <p>HTTP-проверки · от 30 секунд до 1 часа</p>
            </div>
            {filteredGroup ? (
              <button onClick={() => setGroupFilter(null)}>
                Все мониторы · {filteredGroup.name}
              </button>
            ) : (
              <span className="subtle">Последние наблюдения</span>
            )}
          </div>
          <div className="monitor-toolbar">
            <label>
              Поиск мониторов
              <input
                type="search"
                value={search}
                onChange={(e) => setSearch(e.target.value)}
                placeholder="Название или URL"
              />
            </label>
            <label>
              Статус
              <select
                value={statusFilter}
                onChange={(e) => setStatusFilter(e.target.value)}
              >
                <option value="">Все статусы</option>
                {["UP", "DOWN", "UNKNOWN", "PAUSED"].map((s) => (
                  <option key={s} value={s}>
                    {statusLabel(s)}
                  </option>
                ))}
              </select>
            </label>
            <label>
              Группа
              <select
                value={groupFilter ?? ""}
                onChange={(e) => setGroupFilter(e.target.value || null)}
              >
                <option value="">Все группы</option>
                {groups.map((g) => (
                  <option key={g.id} value={g.id}>
                    {g.name}
                  </option>
                ))}
              </select>
            </label>
            <label>
              Сортировка выборки
              <select value={sort} onChange={(e) => setSort(e.target.value)}>
                <option value="name">По названию</option>
                <option value="status">Статус</option>
                <option value="latency">Сначала медленные</option>
              </select>
            </label>
          </div>
          <p className="selection-note">
            Показано {visible.length} из {monitors.length} загруженных мониторов
            (лимит API: 500). Поиск, сортировка и метрики относятся к этой
            выборке.
          </p>
          <div
            className="table-scroll"
            tabIndex={0}
            role="region"
            aria-label="Таблица с прокруткой"
          >
            <table>
              <thead>
                <tr>
                  <th>Сервис</th>
                  <th>Статус</th>
                  <th>HTTP</th>
                  <th>Время ответа</th>
                  <th>Последняя проверка</th>
                  <th>Доступность за 24 ч</th>
                  <th>Текущее падение</th>
                  <th>Действие</th>
                </tr>
              </thead>
              <tbody>
                {visible.map((m) => (
                  <tr key={m.id}>
                    <td>
                      <button
                        className="monitor-name"
                        onClick={() => {
                          setResults([]);
                          setSelected(m);
                        }}
                      >
                        {m.name}
                      </button>
                      <div className="url">{m.url}</div>
                    </td>
                    <td>
                      <span className={`badge ${m.state.toLowerCase()}`}>
                        ● {statusLabel(m.state)}
                      </span>
                      {maintenance.active_monitor_ids?.includes(m.id) && (
                        <small
                          className="maintenance-badge"
                          title="Рассылка по одному или нескольким маршрутам подавлена; реальный статус сохранён."
                        >
                          ОБСЛУЖИВАНИЕ
                        </small>
                      )}
                    </td>
                    <td className="mono">{m.last_status_code ?? "—"}</td>
                    <td className="mono">
                      {m.last_response_ms == null
                        ? "—"
                        : `${Math.round(m.last_response_ms)} мс`}
                    </td>
                    <td>
                      {m.last_checked_at
                        ? new Date(m.last_checked_at).toLocaleTimeString(
                            "ru-RU",
                          )
                        : "Ожидание первой проверки"}
                    </td>
                    <td
                      title={
                        uptime[m.id]
                          ? `${uptime[m.id].samples} наблюдений; по проверкам, обновление каждые 30 с`
                          : "Наблюдений пока нет"
                      }
                    >
                      {uptime[m.id]
                        ? `${uptime[m.id].percent.toFixed(2)}%`
                        : "НЕТ ДАННЫХ"}
                    </td>
                    <td>
                      {m.state === "DOWN" ? (
                        <OutageDuration started={overview?.opened_at?.[m.id]} />
                      ) : (
                        "—"
                      )}
                    </td>
                    <td>
                      <button
                        className="run"
                        disabled={
                          busy ||
                          m.state === "PAUSED" ||
                          m.run_requested ||
                          m.is_running
                        }
                        onClick={() => action(m, "run")}
                      >
                        Проверить сейчас ↗
                      </button>
                      <div className="row-actions">
                        <button
                          disabled={busy}
                          onClick={() => {
                            setEditing(m);
                            setForm(true);
                          }}
                        >
                          Изменить
                        </button>
                        <button
                          disabled={busy}
                          onClick={() =>
                            action(m, m.state === "PAUSED" ? "resume" : "pause")
                          }
                        >
                          {m.state === "PAUSED"
                            ? "Возобновить"
                            : "Приостановить"}
                        </button>
                        <button
                          className="danger"
                          disabled={busy}
                          onClick={() => action(m, "delete")}
                        >
                          Удалить
                        </button>
                      </div>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
          {!visible.length && (
            <div className="empty">
              <div className="empty-icon">⌁</div>
              <h3>
                {loading
                  ? "Загрузка мониторов…"
                  : filteredGroup
                    ? "В этой группе нет мониторов"
                    : "Добавьте первый сервис"}
              </h3>
              <p>
                {loading
                  ? "Подключение к API мониторинга."
                  : "Добавьте URL. Worker выполнит HTTP-проверки и сохранит результаты."}
              </p>
              {!loading && (
                <button onClick={() => setForm(true)}>
                  + Добавить первый монитор
                </button>
              )}
            </div>
          )}
          <div className="table-footer">
            <span>● Наблюдения сохраняются в PostgreSQL</span>
            <span>Без вымышленных метрик доступности</span>
          </div>
        </section>
        {current && (
          <section className="panel detail">
            <div className="section-heading">
              <div>
                <h2>{current.name}</h2>
                <p>
                  {current.url} · интервал {current.interval_seconds}с · таймаут{" "}
                  {current.timeout_seconds}с
                </p>
              </div>
              <button onClick={() => setSelected(null)}>
                Закрыть сведения
              </button>
            </div>
            <AnalyticsPanel
              base={`/api/monitors/${current.id}/analytics`}
              revision={current.last_checked_at}
            />
            <h3>Последние наблюдения</h3>
            {historyLoading ? (
              <p>Загрузка истории…</p>
            ) : !results.length ? (
              <p>Наблюдений пока нет.</p>
            ) : (
              <div
                className="table-scroll"
                tabIndex={0}
                role="region"
                aria-label="Таблица с прокруткой"
              >
                <table>
                  <thead>
                    <tr>
                      <th>Время наблюдения</th>
                      <th>Результат</th>
                      <th>HTTP</th>
                      <th>Время ответа</th>
                      <th>Причина</th>
                    </tr>
                  </thead>
                  <tbody>
                    {results.map((r) => (
                      <tr key={r.id}>
                        <td>
                          {new Date(r.checked_at).toLocaleString("ru-RU")}
                        </td>
                        <td className={r.success ? "green" : "red"}>
                          {r.success ? "Успешно" : "Ошибка"}
                        </td>
                        <td>{r.status_code ?? "—"}</td>
                        <td>{r.response_ms} мс</td>
                        <td>{reasonLabel(r.error)}</td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            )}
            <p className="subtle">
              Последние 100 отдельных проверок. Графики выше используют
              агрегацию всего выбранного периода в PostgreSQL.
            </p>
          </section>
        )}
        <NotificationsPanel active={activeSection === "notifications"} />
        <PublicationPanel monitors={monitors} />
        <IncidentsPanel revision={incidentRevision} monitors={monitors} />
        <MaintenancePanel
          monitors={monitors}
          groups={groups}
          revision={maintenanceRevision}
          onSnapshot={setMaintenance}
        />
        <GroupsPanel
          groups={groups}
          maintenanceGroupIds={maintenance.active_group_ids ?? []}
          monitors={monitors}
          onChange={groupChanged}
          onFilter={(id) => {
            setGroupFilter(id);
            location.hash = "monitors";
            document
              .getElementById("monitors")
              ?.scrollIntoView({ behavior: "instant" });
          }}
          notify={setNotice}
        />
        <div className="bottom-note">
          <span>РЕАЛЬНЫЕ ПРОВЕРКИ. ПРОВЕРЯЕМЫЕ ДАННЫЕ.</span>
          <span>Локальное окружение · закрытая консоль управления</span>
        </div>
      </main>
    </div>
  );
}
