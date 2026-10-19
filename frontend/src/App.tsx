import { useEffect, useState } from "react";
import type { FormEvent } from "react";

export type Monitor = {
  id: string;
  name: string;
  url: string;
  state: string;
  interval_seconds: number;
  timeout_seconds: number;
  last_status_code: number | null;
  last_response_ms: number | null;
  last_checked_at: string | null;
  consecutive_failures: number;
};
type Result = {
  id: string;
  checked_at: string;
  success: boolean;
  status_code: number | null;
  response_ms: number;
  error: string | null;
};

async function request<T>(path: string, options?: RequestInit): Promise<T> {
  const response = await fetch(`/api${path}`, options);
  if (!response.ok) {
    let message = `Request failed (${response.status})`;
    try {
      const data = await response.json();
      if (typeof data.detail === "string") message = data.detail;
    } catch {
      /* no JSON error body */
    }
    throw new Error(message);
  }
  return response.status === 204 ? (undefined as T) : response.json();
}

export function App() {
  const [monitors, setMonitors] = useState<Monitor[]>([]);
  const [loading, setLoading] = useState(true);
  const [connection, setConnection] = useState("Connecting");
  const [error, setError] = useState("");
  const [form, setForm] = useState(false);
  const [busy, setBusy] = useState(false);
  const [selected, setSelected] = useState<Monitor | null>(null);
  const [results, setResults] = useState<Result[]>([]);
  const [historyLoading, setHistoryLoading] = useState(false);

  useEffect(() => {
    let active = true;
    let receivedSnapshot = false;
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
      events.onopen = () => setConnection("Live");
      events.onmessage = (event) => {
        try {
          receivedSnapshot = true;
          setMonitors(JSON.parse(event.data));
          setLoading(false);
          setConnection("Live");
        } catch {
          setConnection("Invalid update");
        }
      };
      events.onerror = () => setConnection("Reconnecting");
    };
    const offline = () => {
      events?.close();
      setConnection("Reconnecting");
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

  async function create(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setBusy(true);
    setError("");
    const data = new FormData(event.currentTarget);
    try {
      const monitor = await request<Monitor>("/monitors", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          name: data.get("name"),
          url: data.get("url"),
          interval_seconds: Number(data.get("interval")),
          timeout_seconds: Number(data.get("timeout")),
          expected_status: Number(data.get("status")),
          expected_body: data.get("body") || null,
        }),
      });
      setMonitors((previous) => [
        ...previous.filter((m) => m.id !== monitor.id),
        monitor,
      ]);
      setForm(false);
    } catch (e) {
      setError((e as Error).message);
    } finally {
      setBusy(false);
    }
  }

  async function run(id: string) {
    setBusy(true);
    setError("");
    try {
      await request(`/monitors/${id}/run`, { method: "POST" });
    } catch (e) {
      setError((e as Error).message);
    } finally {
      setBusy(false);
    }
  }

  const counts = ["UP", "DOWN", "UNKNOWN", "PAUSED"].map(
    (state) => monitors.filter((m) => m.state === state).length,
  );
  const current = monitors.find((m) => m.id === selected?.id) || selected;
  return (
    <div className="shell">
      <aside>
        <a className="brand" href="#overview">
          <span className="brand-icon">ϟ</span> ServicePulse
        </a>
        <div className="workspace">
          LOCAL WORKSPACE <span>01</span>
        </div>
        <nav aria-label="Main">
          <a className="active" href="#overview" aria-label="Overview">
            ◉ <span>Overview</span>
          </a>
          <a href="#monitors" aria-label="All monitors">
            ▤ <span>All monitors</span>
            <small>{monitors.length}</small>
          </a>
        </nav>
        <div className="sidebar-note">
          <span className="tag">FIRST CHECKPOINT</span>
          <p>
            Real checks.
            <br />
            Observable results.
          </p>
          <small>
            Incidents, groups and email are planned for the next phases.
          </small>
        </div>
        <footer>
          ServicePulse <span>v0.1</span>
        </footer>
      </aside>
      <main id="overview">
        <header>
          <span>
            Workspace <b>/</b> Overview
          </span>
          <span
            className={`connection ${connection === "Live" ? "live" : ""}`}
            role="status"
          >
            ● {connection}
          </span>
        </header>
        <div className="page-title">
          <div>
            <div className="eyebrow">MONITORING / OVERVIEW</div>
            <h1>
              A clear view of availability<span>.</span>
            </h1>
            <p>
              Your services, observed continuously. Updates arrive
              automatically.
            </p>
          </div>
          <button className="primary" onClick={() => setForm(!form)}>
            {form ? "Close form" : "+ Add monitor"}
          </button>
        </div>
        {error && (
          <div className="error" role="alert">
            {error}
            <button onClick={() => setError("")} aria-label="Dismiss error">
              ×
            </button>
          </div>
        )}
        {form && (
          <section className="panel form-panel">
            <h2>New monitor</h2>
            <form onSubmit={create}>
              <div className="fields">
                <label>
                  Name
                  <input
                    name="name"
                    required
                    maxLength={120}
                    placeholder="API / production"
                  />
                </label>
                <label className="wide">
                  URL
                  <input
                    name="url"
                    type="url"
                    required
                    maxLength={2048}
                    placeholder="https://example.com/health"
                  />
                </label>
                <label>
                  Interval (seconds)
                  <input
                    name="interval"
                    type="number"
                    min={30}
                    max={3600}
                    defaultValue={30}
                    required
                  />
                </label>
                <label>
                  Timeout (seconds)
                  <input
                    name="timeout"
                    type="number"
                    min={0.1}
                    max={120}
                    step={0.1}
                    defaultValue={5}
                    required
                  />
                </label>
                <label>
                  Expected HTTP status
                  <input
                    name="status"
                    type="number"
                    min={100}
                    max={599}
                    defaultValue={200}
                    required
                  />
                </label>
                <label className="wide">
                  Expected text (optional)
                  <input name="body" maxLength={1000} />
                </label>
              </div>
              <div className="form-actions">
                <small>Two consecutive failures confirm a DOWN state.</small>
                <button className="primary" disabled={busy}>
                  {busy ? "Creating…" : "Create monitor"}
                </button>
              </div>
            </form>
          </section>
        )}
        <section className="stats" aria-label="Monitor summary">
          {[
            "Total monitors",
            "Operational",
            "Down",
            "Awaiting data",
            "Paused",
          ].map((label, i) => (
            <article key={label}>
              <span>{label}</span>
              <strong
                className={
                  i === 1 ? "green" : i === 2 && counts[1] ? "red" : ""
                }
              >
                {i === 0 ? monitors.length : counts[i - 1]}
              </strong>
              <small>
                {i === 0
                  ? "In this workspace"
                  : i === 1
                    ? "Successful observations"
                    : i === 2
                      ? "Threshold confirmed"
                      : i === 3
                        ? "No confirmed state yet"
                        : "Checks suspended"}
              </small>
            </article>
          ))}
        </section>
        <section className="panel" id="monitors">
          <div className="section-heading">
            <div>
              <h2>
                Service monitors <span>{monitors.length}</span>
              </h2>
              <p>HTTP checks · 30 seconds to 1 hour</p>
            </div>
            <span className="subtle">Latest observations</span>
          </div>
          <div className="table-scroll">
            <table>
              <thead>
                <tr>
                  <th>Service</th>
                  <th>Status</th>
                  <th>HTTP</th>
                  <th>Response</th>
                  <th>Last checked</th>
                  <th>Action</th>
                </tr>
              </thead>
              <tbody>
                {monitors.map((m) => (
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
                        ● {m.state}
                      </span>
                    </td>
                    <td className="mono">{m.last_status_code ?? "—"}</td>
                    <td className="mono">
                      {m.last_response_ms == null
                        ? "—"
                        : `${Math.round(m.last_response_ms)} ms`}
                    </td>
                    <td>
                      {m.last_checked_at
                        ? new Date(m.last_checked_at).toLocaleTimeString()
                        : "Awaiting first check"}
                    </td>
                    <td>
                      <button
                        className="run"
                        disabled={busy}
                        onClick={() => run(m.id)}
                      >
                        Run now ↗
                      </button>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
          {!monitors.length && (
            <div className="empty">
              <div className="empty-icon">⌁</div>
              <h3>
                {loading
                  ? "Loading monitors…"
                  : "Start with your first service"}
              </h3>
              <p>
                {loading
                  ? "Connecting to the monitoring API."
                  : "Add a URL. The worker will check it and save each observation."}
              </p>
              {!loading && (
                <button onClick={() => setForm(true)}>
                  + Add your first monitor
                </button>
              )}
            </div>
          )}
          <div className="table-footer">
            <span>● Observations are persisted in PostgreSQL</span>
            <span>No synthetic uptime metrics</span>
          </div>
        </section>
        {current && (
          <section className="panel detail">
            <div className="section-heading">
              <div>
                <h2>{current.name}</h2>
                <p>
                  {current.url} · every {current.interval_seconds}s · timeout{" "}
                  {current.timeout_seconds}s
                </p>
              </div>
              <button onClick={() => setSelected(null)}>Close details</button>
            </div>
            <h3>Recent observations</h3>
            {historyLoading ? (
              <p>Loading history…</p>
            ) : !results.length ? (
              <p>No observations yet.</p>
            ) : (
              <div className="table-scroll">
                <table>
                  <thead>
                    <tr>
                      <th>Observed at</th>
                      <th>Result</th>
                      <th>HTTP</th>
                      <th>Response</th>
                      <th>Reason</th>
                    </tr>
                  </thead>
                  <tbody>
                    {results.map((r) => (
                      <tr key={r.id}>
                        <td>{new Date(r.checked_at).toLocaleString()}</td>
                        <td className={r.success ? "green" : "red"}>
                          {r.success ? "Success" : "Failure"}
                        </td>
                        <td>{r.status_code ?? "—"}</td>
                        <td>{r.response_ms} ms</td>
                        <td>{r.error ?? "—"}</td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            )}
            <p className="subtle">
              Most recent 100 checks. Monthly charts and incident history are
              not available in this checkpoint.
            </p>
          </section>
        )}
        <div className="bottom-note">
          <span>BUILT TO KNOW, NOT TO GUESS.</span>
          <span>Local development · private management console</span>
        </div>
      </main>
    </div>
  );
}
