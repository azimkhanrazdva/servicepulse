import { useState } from "react";
import type { FormEvent } from "react";
import { ApiError, request } from "./api";
import type { Monitor } from "./api";

export function MonitorForm({
  initial,
  onSaved,
  onCancel,
  onBusyChange,
}: {
  initial?: Monitor;
  onSaved: (monitor: Monitor) => void;
  onCancel: () => void;
  onBusyChange?: (busy: boolean) => void;
}) {
  const [source, setSource] = useState(initial);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");
  const [conflict, setConflict] = useState(false);
  async function save(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    if (busy) return;
    setBusy(true);
    onBusyChange?.(true);
    setError("");
    setConflict(false);
    const form = new FormData(event.currentTarget);
    const payload = {
      name: form.get("name"),
      url: form.get("url"),
      interval_seconds: Number(form.get("interval")),
      timeout_seconds: Number(form.get("timeout")),
      expected_status: Number(form.get("status")),
      expected_body: form.get("body") || null,
      failure_threshold: Number(form.get("threshold")),
      ...(source ? { config_version: source.config_version } : {}),
    };
    try {
      const monitor = await request<Monitor>(
        source ? `/monitors/${source.id}` : "/monitors",
        {
          method: source ? "PUT" : "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify(payload),
        },
      );
      onSaved(monitor);
    } catch (e) {
      setError((e as Error).message);
      setConflict(e instanceof ApiError && e.status === 409);
    } finally {
      setBusy(false);
      onBusyChange?.(false);
    }
  }
  async function reload() {
    setBusy(true);
    onBusyChange?.(true);
    try {
      setSource(await request<Monitor>(`/monitors/${source!.id}`));
      setConflict(false);
      setError("");
    } catch (e) {
      setError((e as Error).message);
    } finally {
      setBusy(false);
      onBusyChange?.(false);
    }
  }
  return (
    <section className="panel form-panel" aria-label="Настройка монитора">
      <h2>{source ? "Изменить монитор" : "Новый монитор"}</h2>
      {error && (
        <p className="error" role="alert">
          {error}
        </p>
      )}
      {conflict && (
        <button disabled={busy} onClick={reload}>
          Отменить черновик и загрузить заново
        </button>
      )}
      <form key={source?.config_version ?? "new"} onSubmit={save}>
        <div className="fields">
          <label>
            Название
            <input
              name="name"
              required
              maxLength={120}
              defaultValue={source?.name}
              placeholder="API / основной сервис"
            />
          </label>
          <label className="wide">
            URL
            <input
              name="url"
              type="url"
              required
              maxLength={2048}
              defaultValue={source?.url}
              placeholder="https://example.com/health"
            />
          </label>
          <label>
            Интервал (секунды)
            <input
              name="interval"
              type="number"
              min={30}
              max={3600}
              defaultValue={source?.interval_seconds ?? 30}
              required
            />
          </label>
          <label>
            Таймаут (секунды)
            <input
              name="timeout"
              type="number"
              min={0.1}
              max={120}
              step={0.1}
              defaultValue={source?.timeout_seconds ?? 5}
              required
            />
          </label>
          <label>
            Ожидаемый HTTP-код
            <input
              name="status"
              type="number"
              min={100}
              max={599}
              defaultValue={source?.expected_status ?? 200}
              required
            />
          </label>
          <label className="wide">
            Ожидаемый текст (необязательно)
            <input
              name="body"
              maxLength={1000}
              defaultValue={source?.expected_body ?? ""}
            />
          </label>
          <label>
            Ошибок для подтверждения падения
            <input
              name="threshold"
              type="number"
              min={1}
              max={10}
              defaultValue={source?.failure_threshold ?? 2}
              required
            />
          </label>
        </div>
        <div className="form-actions">
          <small>
            Изменения сбрасывают текущий статус; прежние наблюдения сохраняются.
          </small>
          <div className="actions">
            <button type="button" onClick={onCancel} disabled={busy}>
              Отмена
            </button>
            <button className="primary" disabled={busy}>
              {busy
                ? "Сохранение…"
                : source
                  ? "Сохранить монитор"
                  : "Создать монитор"}
            </button>
          </div>
        </div>
      </form>
    </section>
  );
}
