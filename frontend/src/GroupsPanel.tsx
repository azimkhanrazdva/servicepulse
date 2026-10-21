import { statusLabel } from "./ru";
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
  maintenanceGroupIds = [],
}: {
  groups: Group[];
  monitors: Monitor[];
  onChange: (group: Group | string) => void;
  onFilter: (id: string) => void;
  notify: (message: string) => void;
  maintenanceGroupIds?: string[];
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
      notify(current ? "Группа обновлена." : "Группа создана.");
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
        `Удалить группу «${group.name}»? Мониторы и наблюдения сохранятся.`,
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
      notify("Группа удалена. Мониторы сохранены.");
    } catch (e) {
      setError((e as Error).message);
    } finally {
      setBusy(false);
    }
  }
  return (
    <section className="panel" id="groups" aria-label="Группы мониторов">
      <div className="section-heading">
        <div>
          <h2>
            Группы мониторов <span>{groups.length}</span>
          </h2>
          <p>Доступность групп и получатели уведомлений</p>
        </div>
        <button onClick={() => edit("new")}>+ Добавить группу</button>
      </div>
      {error && (
        <p className="error" role="alert">
          {error}
        </p>
      )}
      {editor && (
        <div className="form-panel">
          <h3>{current ? "Изменить группу" : "Новая группа"}</h3>
          {conflict && (
            <button disabled={busy} onClick={reload}>
              Отменить черновик группы и загрузить заново
            </button>
          )}
          <form
            key={current ? `${current.id}-${current.config_version}` : "new"}
            onSubmit={save}
          >
            <div className="fields">
              <label>
                Название группы
                <input
                  name="name"
                  required
                  maxLength={120}
                  defaultValue={current?.name}
                />
              </label>
              <label className="wide">
                Получатели (по одному в строке)
                <textarea
                  name="recipients"
                  rows={3}
                  defaultValue={current?.recipients.join("\n") ?? ""}
                />
              </label>
            </div>
            <fieldset>
              <legend>Мониторы группы</legend>
              {!monitors.length && (
                <p>Сначала добавьте монитор или сохраните пустую группу.</p>
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
                    {m.name} <small>· {statusLabel(m.state)}</small>
                  </span>
                </label>
              ))}
            </fieldset>
            <div className="form-actions">
              <small>
                Локальная почта поступает в Mailpit. Обслуживание подавляет
                соответствующие маршруты. Новые получатели действуют для будущих
                инцидентов; удаление отменяет ожидающие письма.
              </small>
              <div className="actions">
                <button
                  type="button"
                  onClick={() => edit(null)}
                  disabled={busy}
                >
                  Отменить группу
                </button>
                <button className="primary" disabled={busy}>
                  {busy
                    ? "Сохранение…"
                    : current
                      ? "Сохранить группу"
                      : "Создать группу"}
                </button>
              </div>
            </div>
          </form>
        </div>
      )}
      <div className="group-grid">
        {!groups.length && (
          <p className="group-empty">
            Групп пока нет. Объединяйте мониторы без изменения параметров
            проверок.
          </p>
        )}
        {groups.map((g) => (
          <article className="group-card" key={g.id}>
            <div>
              <h3>{g.name}</h3>
              {maintenanceGroupIds.includes(g.id) && (
                <small className="maintenance-badge">ОБСЛУЖИВАНИЕ</small>
              )}
              <span className={`badge ${g.state.toLowerCase()}`}>
                ● {statusLabel(g.state)}
              </span>
            </div>
            <p>
              {g.monitor_ids.length} мониторов · {g.recipients.length}{" "}
              получателей почты
            </p>
            <p className="subtle">
              {g.recipients.join(", ") || "Получатели почты не настроены."}
            </p>
            <div className="actions">
              <button onClick={() => onFilter(g.id)}>Показать мониторы</button>
              <button onClick={() => edit(g)} disabled={busy}>
                Изменить группу
              </button>
              <button
                className="danger"
                onClick={() => remove(g)}
                disabled={busy}
              >
                Удалить группу
              </button>
            </div>
          </article>
        ))}
      </div>
    </section>
  );
}
