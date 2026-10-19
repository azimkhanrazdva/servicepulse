import { useEffect, useState } from "react";
import { request } from "./api";
import type { Monitor, Group } from "./api";
import { MonitorForm } from "./MonitorForm";
import { GroupsPanel } from "./GroupsPanel";

type Result = {
  id: string;
  checked_at: string;
  success: boolean;
  status_code: number | null;
  response_ms: number;
  error: string | null;
};

export function App() {
  const [monitors, setMonitors] = useState<Monitor[]>([]);
  const [loading, setLoading] = useState(true);
  const [connection, setConnection] = useState("Connecting");
  const [error, setError] = useState("");
  const [form, setForm] = useState(false);
  const [busy, setBusy] = useState(false);
  const [editing, setEditing] = useState<Monitor | undefined>();
  const [groups, setGroups] = useState<Group[]>([]);
  const [groupFilter, setGroupFilter] = useState<string | null>(null);
  const [notice, setNotice] = useState("");
  const [selected, setSelected] = useState<Monitor | null>(null);
  const [results, setResults] = useState<Result[]>([]);
  const [historyLoading, setHistoryLoading] = useState(false);

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
      events.addEventListener("groups", (event) => {
        try {
          receivedGroups = true;
          setGroups(JSON.parse((event as MessageEvent).data));
        } catch {
          setError("Could not read the group update.");
        }
      });
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

  async function action(
    monitor: Monitor,
    operation: "run" | "pause" | "resume" | "delete",
  ) {
    if (
      operation === "delete" &&
      !window.confirm(
        `Delete monitor “${monitor.name}” and its observation history?`,
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
          ? "Check queued."
          : operation === "delete"
            ? "Monitor deleted."
            : operation === "pause"
              ? "Monitor paused."
              : "Monitor resumed.",
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
    setNotice("Monitor saved.");
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
  const visible = filteredGroup
    ? monitors.filter((m) => filteredGroup.monitor_ids.includes(m.id))
    : monitors;
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
        <a className="group-nav" href="#groups">
          Groups
        </a>
        <div className="sidebar-note">
          <span className="tag">MANAGEMENT / V0.2</span>
          <p>
            Real checks.
            <br />
            Observable results.
          </p>
          <small>Incidents and email are planned for the next phases.</small>
        </div>
        <footer>
          ServicePulse <span>v0.2</span>
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
          <button
            className="primary"
            onClick={() => {
              setEditing(undefined);
              setForm(!form);
            }}
          >
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
        {notice && (
          <div className="notice" aria-live="polite">
            {notice}
            <button
              aria-label="Dismiss confirmation"
              onClick={() => setNotice("")}
            >
              ×
            </button>
          </div>
        )}
        {form && (
          <MonitorForm
            key={editing?.id ?? "new"}
            initial={editing}
            onSaved={saved}
            onCancel={() => {
              setForm(false);
              setEditing(undefined);
            }}
          />
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
                Service monitors <span>{visible.length}</span>
              </h2>
              <p>HTTP checks · 30 seconds to 1 hour</p>
            </div>
            {filteredGroup ? (
              <button onClick={() => setGroupFilter(null)}>
                Show all monitors · {filteredGroup.name}
              </button>
            ) : (
              <span className="subtle">Latest observations</span>
            )}
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
                        disabled={
                          busy ||
                          m.state === "PAUSED" ||
                          m.run_requested ||
                          m.is_running
                        }
                        onClick={() => action(m, "run")}
                      >
                        Run now ↗
                      </button>
                      <div className="row-actions">
                        <button
                          disabled={busy}
                          onClick={() => {
                            setEditing(m);
                            setForm(true);
                          }}
                        >
                          Edit
                        </button>
                        <button
                          disabled={busy}
                          onClick={() =>
                            action(m, m.state === "PAUSED" ? "resume" : "pause")
                          }
                        >
                          {m.state === "PAUSED" ? "Resume" : "Pause"}
                        </button>
                        <button
                          className="danger"
                          disabled={busy}
                          onClick={() => action(m, "delete")}
                        >
                          Delete
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
                  ? "Loading monitors…"
                  : filteredGroup
                    ? "No monitors in this group"
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
        <GroupsPanel
          groups={groups}
          monitors={monitors}
          onChange={groupChanged}
          onFilter={(id) => {
            setGroupFilter(id);
            document
              .getElementById("monitors")
              ?.scrollIntoView({ behavior: "instant" });
          }}
          notify={setNotice}
        />
        <div className="bottom-note">
          <span>BUILT TO KNOW, NOT TO GUESS.</span>
          <span>Local development · private management console</span>
        </div>
      </main>
    </div>
  );
}
