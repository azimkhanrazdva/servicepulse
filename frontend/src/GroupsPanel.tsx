import { useState } from "react";
import type { FormEvent } from "react";
import { ApiError, request } from "./api";
import type { Group, Monitor } from "./api";

export function GroupsPanel({
  groups,
  monitors,
  onChange,
  onFilter,
  notify,
}: {
  groups: Group[];
  monitors: Monitor[];
  onChange: (group: Group | string) => void;
  onFilter: (id: string) => void;
  notify: (message: string) => void;
}) {
  const [editor, setEditor] = useState<Group | "new" | null>(null);
  const [error, setError] = useState("");
  const [busy, setBusy] = useState(false);
  const [conflict, setConflict] = useState(false);
  const current = editor && editor !== "new" ? editor : null;
  function edit(value: Group | "new" | null) {
    setEditor(value);
    setError("");
    setConflict(false);
  }
  async function save(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setBusy(true);
    setError("");
    setConflict(false);
    const form = new FormData(event.currentTarget);
    try {
      const group = await request<Group>(
        current ? `/groups/${current.id}` : "/groups",
        {
          method: current ? "PUT" : "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({
            name: form.get("name"),
            monitor_ids: form.getAll("members"),
            recipients: String(form.get("recipients"))
              .split(/[\n,;]+/)
              .map((s) => s.trim())
              .filter(Boolean),
            ...(current ? { config_version: current.config_version } : {}),
          }),
        },
      );
      onChange(group);
      edit(null);
      notify(current ? "Group updated." : "Group created.");
    } catch (e) {
      setError((e as Error).message);
      setConflict(e instanceof ApiError && e.status === 409);
    } finally {
      setBusy(false);
    }
  }
  async function reload() {
    setBusy(true);
    try {
      edit(await request<Group>(`/groups/${current!.id}`));
    } catch (e) {
      setError((e as Error).message);
    } finally {
      setBusy(false);
    }
  }
  async function remove(group: Group) {
    if (
      !window.confirm(
        `Delete group “${group.name}”? Monitors and observations will be retained.`,
      )
    )
      return;
    setBusy(true);
    setError("");
    try {
      await request(
        `/groups/${group.id}?config_version=${group.config_version}`,
        { method: "DELETE" },
      );
      onChange(group.id);
      if (current?.id === group.id) edit(null);
      notify("Group deleted. Monitors retained.");
    } catch (e) {
      setError((e as Error).message);
    } finally {
      setBusy(false);
    }
  }
  return (
    <section className="panel" id="groups" aria-label="Monitor groups">
      <div className="section-heading">
        <div>
          <h2>
            Monitor groups <span>{groups.length}</span>
          </h2>
          <p>Group availability and notification recipients</p>
        </div>
        <button onClick={() => edit("new")}>+ Add group</button>
      </div>
      {error && (
        <p className="error" role="alert">
          {error}
        </p>
      )}
      {editor && (
        <div className="form-panel">
          <h3>{current ? "Edit group" : "New group"}</h3>
          {conflict && (
            <button disabled={busy} onClick={reload}>
              Discard group draft and reload
            </button>
          )}
          <form
            key={current ? `${current.id}-${current.config_version}` : "new"}
            onSubmit={save}
          >
            <div className="fields">
              <label>
                Group name
                <input
                  name="name"
                  required
                  maxLength={120}
                  defaultValue={current?.name}
                />
              </label>
              <label className="wide">
                Recipients (one per line)
                <textarea
                  name="recipients"
                  rows={3}
                  defaultValue={current?.recipients.join("\n") ?? ""}
                />
              </label>
            </div>
            <fieldset>
              <legend>Group members</legend>
              {!monitors.length && (
                <p>Add a monitor first, or save an empty group.</p>
              )}
              {monitors.map((m) => (
                <label className="check-label" key={m.id}>
                  <input
                    name="members"
                    type="checkbox"
                    value={m.id}
                    defaultChecked={
                      current?.monitor_ids.includes(m.id) ?? false
                    }
                  />
                  <span>
                    {m.name} <small>· {m.state}</small>
                  </span>
                </label>
              ))}
            </fieldset>
            <div className="form-actions">
              <small>
                Recipients are stored. Email delivery is planned for phase 4.
              </small>
              <div className="actions">
                <button
                  type="button"
                  onClick={() => edit(null)}
                  disabled={busy}
                >
                  Cancel group
                </button>
                <button className="primary" disabled={busy}>
                  {busy ? "Saving…" : current ? "Save group" : "Create group"}
                </button>
              </div>
            </div>
          </form>
        </div>
      )}
      <div className="group-grid">
        {!groups.length && (
          <p className="group-empty">
            No groups yet. Organize monitors without changing their check
            settings.
          </p>
        )}
        {groups.map((g) => (
          <article className="group-card" key={g.id}>
            <div>
              <h3>{g.name}</h3>
              <span className={`badge ${g.state.toLowerCase()}`}>
                ● {g.state}
              </span>
            </div>
            <p>
              {g.monitor_ids.length} monitors · {g.recipients.length} email
              recipients
            </p>
            <div className="actions">
              <button onClick={() => onFilter(g.id)}>View monitors</button>
              <button onClick={() => edit(g)} disabled={busy}>
                Edit group
              </button>
              <button
                className="danger"
                onClick={() => remove(g)}
                disabled={busy}
              >
                Delete group
              </button>
            </div>
          </article>
        ))}
      </div>
    </section>
  );
}
