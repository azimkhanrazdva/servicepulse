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
      setError("End must be later than start.");
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
    if (!confirm(`Delete maintenance “${window.name}”?`)) return;
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
    <section
      className="panel"
      id="maintenance"
      aria-label="Maintenance windows"
    >
      <div className="section-heading">
        <div>
          <h2>Maintenance windows</h2>
          <p>Checks continue · only applicable email routes are suppressed</p>
        </div>
        <button onClick={() => edit("new")}>+ Add maintenance</button>
      </div>
      {loadError && (
        <p className="error" role="alert">
          Maintenance refresh failed: {loadError}
        </p>
      )}
      {error && (
        <p className="error" role="alert">
          {error}
        </p>
      )}
      {conflict && (
        <p>
          Your draft is preserved.{" "}
          <button
            onClick={() => {
              edit(null);
              setRefresh((v) => v + 1);
            }}
          >
            Discard maintenance draft and reload
          </button>
        </p>
      )}
      {editor && (
        <form className="form-panel" onSubmit={save} key={current?.id ?? "new"}>
          <h3>{current ? "Edit maintenance" : "New maintenance"}</h3>
          <div className="fields">
            <label>
              Maintenance name
              <input
                name="name"
                required
                maxLength={120}
                defaultValue={current?.name}
              />
            </label>
            <label>
              Target type
              <select
                aria-label="Maintenance target type"
                value={targetType}
                onChange={(e) => setTargetType(e.target.value)}
              >
                <option value="monitor">Monitor</option>
                <option value="group">Group</option>
              </select>
            </label>
            <label>
              Maintenance target
              <select
                name="target"
                required
                key={targetType}
                defaultValue={current?.monitor_id ?? current?.group_id ?? ""}
              >
                <option value="" disabled>
                  Choose a target
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
              Starts at
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
              Ends at
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
            Input timezone: {Intl.DateTimeFormat().resolvedOptions().timeZone}.
            Stored in UTC. Start included; end excluded.
          </p>
          <div className="actions">
            <button type="button" onClick={() => edit(null)}>
              Cancel maintenance
            </button>
            <button className="primary" disabled={busy || conflict}>
              {current ? "Save maintenance" : "Create maintenance"}
            </button>
          </div>
        </form>
      )}
      <div className="maintenance-toolbar">
        <label>
          Window state
          <select
            aria-label="Window state"
            value={state}
            onChange={(e) => {
              setState(e.target.value);
              setOffset(0);
              setLoading(true);
            }}
          >
            <option value="">All windows</option>
            <option>ACTIVE</option>
            <option>UPCOMING</option>
            <option>ENDED</option>
          </select>
        </label>
      </div>
      {loading ? (
        <p className="maintenance-message">Loading maintenance…</p>
      ) : !page.items?.length ? (
        <p className="maintenance-message">
          No maintenance windows match this view.
        </p>
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
                <th>Name / target</th>
                <th>State</th>
                <th>Starts</th>
                <th>Ends</th>
                <th>Actions</th>
              </tr>
            </thead>
            <tbody>
              {page.items.map((w) => (
                <tr key={w.id} data-testid={`window-${w.id}`}>
                  <td>
                    {w.name}
                    <div className="url">
                      {w.monitor_id
                        ? "Monitor: " +
                          (monitors.find((m) => m.id === w.monitor_id)?.name ??
                            w.monitor_id)
                        : "Group: " +
                          (groups.find((g) => g.id === w.group_id)?.name ??
                            w.group_id)}
                    </div>
                  </td>
                  <td>
                    <span className="badge">{w.state}</span>
                  </td>
                  <td>{new Date(w.start_at).toLocaleString()}</td>
                  <td>{new Date(w.end_at).toLocaleString()}</td>
                  <td>
                    <div className="row-actions">
                      <button disabled={busy} onClick={() => edit(w)}>
                        Edit maintenance
                      </button>
                      <button disabled={busy} onClick={() => remove(w)}>
                        Delete maintenance
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
          Previous windows
        </button>
        <span>Page {offset / 20 + 1}</span>
        <button
          disabled={!page.has_more || loading}
          onClick={() => setOffset(offset + 20)}
        >
          Next windows
        </button>
      </div>
      <p className="maintenance-message subtle">
        Monitor windows affect every route. Group windows affect that group
        only. Shared addresses receive one email through any eligible route.
      </p>
    </section>
  );
}
