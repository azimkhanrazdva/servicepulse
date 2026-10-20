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

type Result = {
  id: string;
  checked_at: string;
  success: boolean;
  status_code: number | null;
  response_ms: number;
  error: string | null;
};

export function App() {
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
          setError("Could not read maintenance update.");
        }
      });
      events.addEventListener("overview", (event) => {
        try {
          setOverview(JSON.parse((event as MessageEvent).data));
        } catch {
          setOverviewError("Could not read incident summary.");
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
          <a href="#incidents">Incident journal</a>
          <a href="#maintenance">Maintenance</a>
          <a href="#publication">Public status pages</a>
          <a href="#groups">Notification settings</a>
        </nav>
        <a className="group-nav" href="#groups">
          Groups
        </a>
        <div className="sidebar-note">
          <span className="tag">STATUS / V0.5</span>
          <p>
            Real checks.
            <br />
            Observable results.
          </p>
          <small>Local SMTP alerts with scheduled maintenance.</small>
        </div>
        <footer>
          ServicePulse <span>v0.5</span>
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
          <article>
            <span>Active incidents</span>
            <strong className={overview?.active_incidents ? "red" : ""}>
              {overview?.active_incidents ?? "—"}
            </strong>
            <small>Confirmed and still open</small>
          </article>
        </section>
        {overviewError && (
          <p className="error" role="alert">
            Dashboard analytics: {overviewError}
          </p>
        )}
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
                  <th>24h observed uptime</th>
                  <th>Current outage</th>
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
                      {maintenance.active_monitor_ids?.includes(m.id) && (
                        <small
                          className="maintenance-badge"
                          title="One or more notification routes suppressed; real status is unchanged."
                        >
                          MAINTENANCE
                        </small>
                      )}
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
                    <td
                      title={
                        uptime[m.id]
                          ? `${uptime[m.id].samples} observed checks; sample-based, refreshes every 30s`
                          : "No observed samples available"
                      }
                    >
                      {uptime[m.id]
                        ? `${uptime[m.id].percent.toFixed(2)}%`
                        : "NO DATA"}
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
            <AnalyticsPanel
              base={`/api/monitors/${current.id}/analytics`}
              revision={current.last_checked_at}
            />
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
              Most recent 100 raw checks. Charts above aggregate the full
              selected period in PostgreSQL.
            </p>
          </section>
        )}
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
