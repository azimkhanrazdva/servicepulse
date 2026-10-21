import { statusLabel } from "./ru";
import { useEffect, useState } from "react";
import type { FormEvent } from "react";
import { ApiError, request } from "./api";
import type { Group, Monitor } from "./api";

export type Window = {
  id: string;
  name: string;
  monitor_id: string | null;
  group_id: string | null;
  start_at: string;
  end_at: string;
  state: string;
  config_version: number;
};
export type MaintenanceSnapshot = {
  items: Window[];
  has_more: boolean;
  active_monitor_ids: string[];
  active_group_ids: string[];
};

function localInput(value: string) {
  const date = new Date(value);
  return new Date(date.getTime() - date.getTimezoneOffset() * 60000)
    .toISOString()
    .slice(0, 19);
}

export function MaintenancePanel({
  monitors,
  groups,
  revision,
  onSnapshot,
}: {
  monitors: Monitor[];
  groups: Group[];
  revision: number;
  onSnapshot: (data: MaintenanceSnapshot) => void;
}) {
  const [page, setPage] = useState<MaintenanceSnapshot>({
    items: [],
    has_more: false,
    active_monitor_ids: [],
    active_group_ids: [],
  });
  const [state, setState] = useState("");
  const [offset, setOffset] = useState(0);
  const [refresh, setRefresh] = useState(0);
  const [loading, setLoading] = useState(true);
  const [editor, setEditor] = useState<Window | "new" | null>(null);
  const [targetType, setTargetType] = useState("monitor");
  const [error, setError] = useState("");
  const [loadError, setLoadError] = useState("");
  const [conflict, setConflict] = useState(false);
  const [busy, setBusy] = useState(false);
  const current = editor && editor !== "new" ? editor : null;
  useEffect(() => {
    let active = true;
    const params = new URLSearchParams({ limit: "20", offset: String(offset) });
    if (state) params.set("state", state);
    request<MaintenanceSnapshot>(`/maintenance?${params}`)
      .then((data) => {
        if (active) {
          setPage(data);
          onSnapshot(data);
          setLoadError("");
        }
      })
      .catch((e) => {
        if (active) setLoadError(e.message);
      })
      .finally(() => {
        if (active) setLoading(false);
      });
    return () => {
      active = false;
    };
  }, [revision, refresh, state, offset, onSnapshot]);
  function edit(value: Window | "new" | null) {
    setEditor(value);
    setConflict(false);
    setError("");
    setTargetType(
      value && value !== "new" && value.group_id ? "group" : "monitor",
    );
  }
  async function save(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setBusy(true);
    setError("");
    const data = new FormData(event.currentTarget);
    const start = new Date(String(data.get("start")));
    const end = new Date(String(data.get("end")));
    if (!(end > start)) {
      setError("Окончание должно быть позже начала.");
      setBusy(false);
      return;
    }
    try {
      await request(`/maintenance${current ? `/${current.id}` : ""}`, {
        method: current ? "PUT" : "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          name: data.get("name"),
          monitor_id: targetType === "monitor" ? data.get("target") : null,
          group_id: targetType === "group" ? data.get("target") : null,
          start_at: start.toISOString(),
          end_at: end.toISOString(),
          ...(current ? { config_version: current.config_version } : {}),
        }),
      });
      edit(null);
      setRefresh((v) => v + 1);
    } catch (e) {
      setError((e as Error).message);
      if (e instanceof ApiError && e.status === 409) setConflict(true);
    } finally {
      setBusy(false);
    }
  }
  async function remove(window: Window) {
    if (!confirm(`Удалить окно обслуживания «${window.name}”?`)) return;
    setBusy(true);
    setError("");
    try {
      await request(
        `/maintenance/${window.id}?config_version=${window.config_version}`,
        { method: "DELETE" },
      );
      setRefresh((v) => v + 1);
    } catch (e) {
      setError((e as Error).message);
    } finally {
      setBusy(false);
    }
  }
  return (
    <section className="panel" id="maintenance" aria-label="Окна обслуживания">
      <div className="section-heading">
        <div>
          <h2>Окна обслуживания</h2>
          <p>
            Проверки продолжаются · подавляются только соответствующие почтовые
            маршруты
          </p>
        </div>
        <button onClick={() => edit("new")}>+ Добавить обслуживание</button>
      </div>
      {loadError && (
        <p className="error" role="alert">
          Не удалось обновить обслуживание: {loadError}
        </p>
      )}
      {error && (
        <p className="error" role="alert">
          {error}
        </p>
      )}
      {conflict && (
        <p>
          Ваш черновик сохранён.{" "}
          <button
            onClick={() => {
              edit(null);
              setRefresh((v) => v + 1);
            }}
          >
            Отменить черновик обслуживания и загрузить заново
          </button>
        </p>
      )}
      {editor && (
        <form className="form-panel" onSubmit={save} key={current?.id ?? "new"}>
          <h3>{current ? "Изменить обслуживание" : "Новое обслуживание"}</h3>
          <div className="fields">
            <label>
              Название обслуживания
              <input
                name="name"
                required
                maxLength={120}
                defaultValue={current?.name}
              />
            </label>
            <label>
              Тип объекта
              <select
                aria-label="Тип объекта обслуживания"
                value={targetType}
                onChange={(e) => setTargetType(e.target.value)}
              >
                <option value="monitor">Монитор</option>
                <option value="group">Группа</option>
              </select>
            </label>
            <label>
              Объект обслуживания
              <select
                name="target"
                required
                key={targetType}
                defaultValue={current?.monitor_id ?? current?.group_id ?? ""}
              >
                <option value="" disabled>
                  Выберите объект
                </option>
                {(targetType === "monitor" ? monitors : groups).map(
                  (target) => (
                    <option key={target.id} value={target.id}>
                      {target.name}
                    </option>
                  ),
                )}
              </select>
            </label>
            <label>
              Начало
              <input
                name="start"
                type="datetime-local"
                step="1"
                required
                defaultValue={localInput(
                  current?.start_at ?? new Date().toISOString(),
                )}
              />
            </label>
            <label>
              Окончание
              <input
                name="end"
                type="datetime-local"
                step="1"
                required
                defaultValue={localInput(
                  current?.end_at ??
                    new Date(Date.now() + 3600000).toISOString(),
                )}
              />
            </label>
          </div>
          <p className="subtle">
            Часовой пояс ввода:{" "}
            {Intl.DateTimeFormat().resolvedOptions().timeZone}. Хранение в UTC.
            Начало включено, окончание исключено.
          </p>
          <div className="actions">
            <button type="button" onClick={() => edit(null)}>
              Отменить обслуживание
            </button>
            <button className="primary" disabled={busy || conflict}>
              {current ? "Сохранить обслуживание" : "Создать обслуживание"}
            </button>
          </div>
        </form>
      )}
      <div className="maintenance-toolbar">
        <label>
          Состояние окна
          <select
            aria-label="Состояние окна"
            value={state}
            onChange={(e) => {
              setState(e.target.value);
              setOffset(0);
              setLoading(true);
            }}
          >
            <option value="">Все окна</option>
            <option value="ACTIVE">Действует (ACTIVE)</option>
            <option value="UPCOMING">Запланировано (UPCOMING)</option>
            <option value="ENDED">Завершено (ENDED)</option>
          </select>
        </label>
      </div>
      {loading ? (
        <p className="maintenance-message">Загрузка обслуживания…</p>
      ) : !page.items?.length ? (
        <p className="maintenance-message">
          Нет окон обслуживания с выбранными параметрами.
        </p>
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
                <th>Название / объект</th>
                <th>Состояние</th>
                <th>Начало</th>
                <th>Окончание</th>
                <th>Действия</th>
              </tr>
            </thead>
            <tbody>
              {page.items.map((w) => (
                <tr key={w.id} data-testid={`window-${w.id}`}>
                  <td>
                    {w.name}
                    <div className="url">
                      {w.monitor_id
                        ? "Монитор: " +
                          (monitors.find((m) => m.id === w.monitor_id)?.name ??
                            w.monitor_id)
                        : "Группа: " +
                          (groups.find((g) => g.id === w.group_id)?.name ??
                            w.group_id)}
                    </div>
                  </td>
                  <td>
                    <span className="badge">{statusLabel(w.state)}</span>
                  </td>
                  <td>{new Date(w.start_at).toLocaleString("ru-RU")}</td>
                  <td>{new Date(w.end_at).toLocaleString("ru-RU")}</td>
                  <td>
                    <div className="row-actions">
                      <button disabled={busy} onClick={() => edit(w)}>
                        Изменить обслуживание
                      </button>
                      <button disabled={busy} onClick={() => remove(w)}>
                        Удалить обслуживание
                      </button>
                    </div>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
      <div className="maintenance-toolbar actions">
        <button
          disabled={!offset || loading}
          onClick={() => setOffset(offset - 20)}
        >
          Предыдущие окна
        </button>
        <span>Страница {offset / 20 + 1}</span>
        <button
          disabled={!page.has_more || loading}
          onClick={() => setOffset(offset + 20)}
        >
          Следующие окна
        </button>
      </div>
      <p className="maintenance-message subtle">
        Окно монитора действует на все маршруты. Окно группы действует только на
        эту группу. Общий адрес получает одно письмо по любому разрешённому
        маршруту.
      </p>
    </section>
  );
}
