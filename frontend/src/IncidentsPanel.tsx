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
    <section className="panel" id="incidents" aria-label="Incident journal">
      <div className="section-heading">
        <div>
          <h2>Incident journal</h2>
          <p>Confirmed failures · administrative closures shown separately</p>
        </div>
      </div>
      <div className="row-actions">
        <label>
          Incident state{" "}
          <select
            aria-label="Incident state"
            value={state}
            onChange={(e) => {
              setState(e.target.value);
              setOffset(0);
              setLoading(true);
            }}
          >
            <option value="">All incidents</option>
            <option value="OPEN">OPEN</option>
            <option value="CLOSED">CLOSED</option>
          </select>
        </label>
        <label>
          Incident monitor{" "}
          <select
            aria-label="Incident monitor"
            value={monitor}
            onChange={(e) => {
              setMonitor(e.target.value);
              setOffset(0);
              setLoading(true);
            }}
          >
            <option value="">All monitors</option>
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
          Incident history unavailable: {error}. Retrying with live updates.
        </p>
      )}
      {loading ? (
        <p>Loading incidents…</p>
      ) : !page.items?.length ? (
        <p>No incidents match this view.</p>
      ) : (
        <div
          className="table-scroll"
          tabIndex={0}
          role="region"
          aria-label="Scrollable table"
        >
          <table>
            <thead>
              <tr>
                <th>Monitor</th>
                <th>State</th>
                <th>Opened</th>
                <th>Recovered</th>
                <th>Duration</th>
                <th>Closure</th>
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
                      {i.state}
                    </span>
                  </td>
                  <td>{new Date(i.opened_at).toLocaleString()}</td>
                  <td>
                    {i.recovered_at
                      ? new Date(i.recovered_at).toLocaleString()
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
                    s
                  </td>
                  <td>
                    {i.closure_reason ?? "Ongoing"}
                    {i.closed_at && i.closure_reason !== "RECOVERED" && (
                      <small> · {new Date(i.closed_at).toLocaleString()}</small>
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
          Previous incidents
        </button>
        <span>Page {offset / 20 + 1}</span>
        <button
          disabled={!page.has_more || loading}
          onClick={() => {
            setOffset(offset + 20);
            setLoading(true);
          }}
        >
          Next incidents
        </button>
      </div>
      <p className="subtle">
        Start time is threshold confirmation. Closure by pause or configuration
        change does not mean recovery. Alerts use group recipients and local
        Mailpit.
      </p>
    </section>
  );
}
