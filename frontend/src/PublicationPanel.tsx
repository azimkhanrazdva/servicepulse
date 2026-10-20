import { useEffect, useState } from "react";
import type { FormEvent } from "react";
import { ApiError, request } from "./api";
import type { Monitor } from "./api";
type Publication = {
  id?: string;
  monitor_id: string;
  public_name: string;
  show_history: boolean;
};
type Page = {
  id: string;
  slug: string;
  title: string;
  enabled: boolean;
  config_version: number;
  publications: Publication[];
};

export function PublicationPanel({ monitors }: { monitors: Monitor[] }) {
  const [pages, setPages] = useState<Page[]>([]);
  const [editor, setEditor] = useState<Page | "new" | null>(null);
  const [selected, setSelected] = useState<string[]>([]);
  const [error, setError] = useState("");
  const [loadError, setLoadError] = useState("");
  const [busy, setBusy] = useState(false);
  const [refresh, setRefresh] = useState(0);
  const [conflict, setConflict] = useState(false);
  const current = editor && editor !== "new" ? editor : null;
  useEffect(() => {
    let active = true;
    const load = () =>
      request<Page[]>("/status-pages")
        .then((data) => {
          if (active) {
            setPages(data);
            setLoadError("");
          }
        })
        .catch((e) => {
          if (active) setLoadError(e.message);
        });
    void load();
    const timer = setInterval(load, 10000);
    return () => {
      active = false;
      clearInterval(timer);
    };
  }, [refresh]);
  function edit(page: Page | "new" | null) {
    setEditor(page);
    setSelected(
      page && page !== "new" ? page.publications.map((p) => p.monitor_id) : [],
    );
    setError("");
    setConflict(false);
  }
  async function save(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setBusy(true);
    setError("");
    const data = new FormData(event.currentTarget);
    try {
      await request(`/status-pages${current ? `/${current.id}` : ""}`, {
        method: current ? "PUT" : "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          slug: data.get("slug"),
          title: data.get("title"),
          enabled: data.has("enabled"),
          publications: selected.map((id) => ({
            monitor_id: id,
            public_name: data.get(`label-${id}`),
            show_history: data.has(`history-${id}`),
          })),
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
  async function remove(page: Page) {
    if (!confirm(`Delete public status page “${page.title}”?`)) return;
    setBusy(true);
    try {
      await request(
        `/status-pages/${page.id}?config_version=${page.config_version}`,
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
    <section id="publication" className="panel">
      <div className="section-heading">
        <div>
          <h2>Public status pages</h2>
          <p>Private by default · explicitly choose every published service</p>
        </div>
        <button onClick={() => edit("new")}>+ Create status page</button>
      </div>
      {loadError && (
        <p className="error" role="alert">
          Publication settings: {loadError}
        </p>
      )}
      {error && (
        <p className="error" role="alert">
          {error}
        </p>
      )}
      {conflict && (
        <p className="service-note">
          Your publication draft is preserved.{" "}
          <button
            onClick={() => {
              edit(null);
              setRefresh((v) => v + 1);
            }}
          >
            Discard publication draft and reload
          </button>
        </p>
      )}
      {editor && (
        <form
          className="form-panel publication-form"
          key={current?.id ?? "new"}
          onSubmit={save}
        >
          <h3>{current ? "Edit status page" : "New status page"}</h3>
          <div className="fields">
            <label>
              Public page title
              <input
                name="title"
                required
                maxLength={120}
                defaultValue={current?.title}
              />
            </label>
            <label>
              Public page slug
              <input
                name="slug"
                required
                minLength={3}
                maxLength={64}
                pattern="[a-z0-9][a-z0-9-]+[a-z0-9]"
                defaultValue={current?.slug}
              />
            </label>
          </div>
          <label className="check-label">
            <input
              type="checkbox"
              name="enabled"
              defaultChecked={current?.enabled ?? false}
            />
            Page is publicly enabled
          </label>
          <p>
            Only selected monitors are published. Enter a separate public label.
            URLs, groups, recipients and internal errors are never shared.
          </p>
          {!monitors.length && (
            <p>No monitors available. Create a monitor first.</p>
          )}
          {monitors.map((m) => {
            const publication = current?.publications.find(
              (p) => p.monitor_id === m.id,
            );
            const checked = selected.includes(m.id);
            return (
              <div className="publish-choice" key={m.id}>
                <label className="check-label">
                  <input
                    type="checkbox"
                    checked={checked}
                    onChange={(e) =>
                      setSelected((ids) =>
                        e.target.checked
                          ? [...ids, m.id]
                          : ids.filter((id) => id !== m.id),
                      )
                    }
                  />
                  Publish {m.name}
                </label>
                {checked && (
                  <div className="fields">
                    <label>
                      Public label for {m.name}
                      <input
                        name={`label-${m.id}`}
                        required
                        maxLength={120}
                        defaultValue={publication?.public_name ?? ""}
                      />
                    </label>
                    <label className="check-label">
                      <input
                        type="checkbox"
                        name={`history-${m.id}`}
                        defaultChecked={publication?.show_history ?? false}
                      />
                      Publish aggregated history for {m.name}
                    </label>
                  </div>
                )}
              </div>
            );
          })}
          <div className="actions">
            <button className="primary" disabled={busy || conflict}>
              Save publication
            </button>
            <button type="button" onClick={() => edit(null)}>
              Cancel publication
            </button>
          </div>
        </form>
      )}
      {!pages.length && !loadError && (
        <p className="service-note">
          No public status pages. Nothing is published.
        </p>
      )}
      <div className="publication-pages">
        {pages.map((page) => (
          <article className="group-card" key={page.id}>
            <h3>{page.title}</h3>
            <p>
              {page.enabled ? "Enabled" : "Disabled"} ·{" "}
              {page.publications.length} published services
            </p>
            <a
              href={`${location.protocol}//${location.hostname}:8081/status/${page.slug}`}
              target="_blank"
              rel="noreferrer"
            >
              Open public page ↗
            </a>
            <div className="row-actions">
              <button disabled={busy} onClick={() => edit(page)}>
                Edit publication
              </button>
              <button disabled={busy} onClick={() => remove(page)}>
                Delete status page
              </button>
            </div>
          </article>
        ))}
      </div>
    </section>
  );
}
