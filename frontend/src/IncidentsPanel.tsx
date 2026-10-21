import { statusLabel } from "./ru";
import { useEffect, useState } from "react";
import { request } from "./api";
import type { Monitor } from "./api";

export type Incident = {
  id: string;
  monitor_id: string;
  monitor_name: string;
  opened_at: string;
  closed_at: string | null;
  recovered_at: string | null;
  closure_reason: string | null;
  state: "OPEN" | "CLOSED";
};
type Page = { items: Incident[]; has_more: boolean };

export function IncidentsPanel({
  revision,
  monitors,
}: {
  revision: number;
  monitors: Monitor[];
}) {
  const [page, setPage] = useState<Page>({ items: [], has_more: false });
  const [state, setState] = useState("");
  const [monitor, setMonitor] = useState("");
  const [offset, setOffset] = useState(0);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");
  const [clock, setClock] = useState(Date.now());
  useEffect(() => {
    const timer = window.setInterval(() => setClock(Date.now()), 1000);
    return () => window.clearInterval(timer);
  }, []);
  useEffect(() => {
    let active = true;
    const query = new URLSearchParams({ limit: "20", offset: String(offset) });
    if (state) query.set("state", state);
    if (monitor) query.set("monitor_id", monitor);
    request<Page>(`/incidents?${query}`)
      .then((data) => {
        if (active) {
          setPage(data);
          setError("");
        }
      })
      .catch((e) => {
        if (active) setError(e.message);
      })
      .finally(() => {
        if (active) setLoading(false);
      });
    return () => {
      active = false;
    };
  }, [revision, state, monitor, offset]);
  return (
    <section className="panel" id="incidents" aria-label="Журнал инцидентов">
      <div className="section-heading">
        <div>
          <h2>Журнал инцидентов</h2>
          <p>
            Подтверждённые падения · административные закрытия показаны отдельно
          </p>
        </div>
      </div>
      <div className="row-actions">
        <label>
          Состояние инцидента{" "}
          <select
            aria-label="Состояние инцидента"
            value={state}
            onChange={(e) => {
              setState(e.target.value);
              setOffset(0);
              setLoading(true);
            }}
          >
            <option value="">Все инциденты</option>
            <option value="OPEN">Открыт (OPEN)</option>
            <option value="CLOSED">Закрыт (CLOSED)</option>
          </select>
        </label>
        <label>
          Монитор инцидента{" "}
          <select
            aria-label="Монитор инцидента"
            value={monitor}
            onChange={(e) => {
              setMonitor(e.target.value);
              setOffset(0);
              setLoading(true);
            }}
          >
            <option value="">Все мониторы</option>
            {monitors.map((m) => (
              <option key={m.id} value={m.id}>
                {m.name}
              </option>
            ))}
          </select>
        </label>
      </div>
      {error && (
        <p role="alert">
          История инцидентов недоступна: {error}. Повтор при следующем
          обновлении.
        </p>
      )}
      {loading ? (
        <p>Загрузка инцидентов…</p>
      ) : !page.items?.length ? (
        <p>Нет инцидентов с выбранными параметрами.</p>
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
                <th>Монитор</th>
                <th>Состояние</th>
                <th>Начало</th>
                <th>Восстановление</th>
                <th>Длительность</th>
                <th>Причина закрытия</th>
              </tr>
            </thead>
            <tbody>
              {page.items.map((i) => (
                <tr key={i.id} data-testid={`incident-${i.id}`}>
                  <td>{i.monitor_name}</td>
                  <td>
                    <span
                      className={`badge ${i.state === "OPEN" ? "down" : "up"}`}
                    >
                      {statusLabel(i.state)}
                    </span>
                  </td>
                  <td>{new Date(i.opened_at).toLocaleString("ru-RU")}</td>
                  <td>
                    {i.recovered_at
                      ? new Date(i.recovered_at).toLocaleString("ru-RU")
                      : "—"}
                  </td>
                  <td data-testid="incident-duration">
                    {Math.max(
                      0,
                      Math.floor(
                        ((i.closed_at ? Date.parse(i.closed_at) : clock) -
                          Date.parse(i.opened_at)) /
                          1000,
                      ),
                    )}
                    с
                  </td>
                  <td>
                    {i.closure_reason
                      ? statusLabel(i.closure_reason)
                      : "Продолжается"}
                    {i.closed_at && i.closure_reason !== "RECOVERED" && (
                      <small>
                        {" "}
                        · {new Date(i.closed_at).toLocaleString("ru-RU")}
                      </small>
                    )}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
      <div className="row-actions">
        <button
          disabled={offset === 0 || loading}
          onClick={() => {
            setOffset(offset - 20);
            setLoading(true);
          }}
        >
          Предыдущие инциденты
        </button>
        <span>Страница {offset / 20 + 1}</span>
        <button
          disabled={!page.has_more || loading}
          onClick={() => {
            setOffset(offset + 20);
            setLoading(true);
          }}
        >
          Следующие инциденты
        </button>
      </div>
      <p className="subtle">
        Начало инцидента фиксируется при подтверждении порога ошибок. Пауза и
        изменение настроек не означают восстановление. Письма получателям групп
        принимает локальный Mailpit.
      </p>
    </section>
  );
}
