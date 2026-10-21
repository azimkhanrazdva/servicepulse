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
  const [copied, setCopied] = useState<string | null>(null);
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
    if (!confirm(`Удалить публичную страницу «${page.title}”?`)) return;
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
          <h2>Публичные страницы</h2>
          <p>По умолчанию закрыто · явно выберите каждый публикуемый сервис</p>
        </div>
        <button onClick={() => edit("new")}>+ Создать страницу</button>
      </div>
      {loadError && (
        <p className="error" role="alert">
          Настройки публикации: {loadError}
        </p>
      )}
      {error && (
        <p className="error" role="alert">
          {error}
        </p>
      )}
      {conflict && (
        <p className="service-note">
          Ваш черновик публикации сохранён.{" "}
          <button
            onClick={() => {
              edit(null);
              setRefresh((v) => v + 1);
            }}
          >
            Отменить черновик публикации и загрузить заново
          </button>
        </p>
      )}
      {editor && (
        <form
          className="form-panel publication-form"
          key={current?.id ?? "new"}
          onSubmit={save}
        >
          <h3>{current ? "Изменить страницу" : "Новая страница состояния"}</h3>
          <div className="fields">
            <label>
              Заголовок публичной страницы
              <input
                name="title"
                required
                maxLength={120}
                defaultValue={current?.title}
              />
            </label>
            <label>
              Адрес страницы (slug)
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
            Разрешить публичный доступ к странице
          </label>
          <p>
            Публикуются только выбранные мониторы. Укажите отдельное публичное
            название. URL, группы, получатели и внутренние ошибки не
            публикуются.
          </p>
          {!monitors.length && (
            <p>Мониторов пока нет. Сначала создайте монитор.</p>
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
                  Опубликовать {m.name}
                </label>
                {checked && (
                  <div className="fields">
                    <label>
                      Публичное название для {m.name}
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
                      Опубликовать агрегированную историю для {m.name}
                    </label>
                  </div>
                )}
              </div>
            );
          })}
          <div className="actions">
            <button className="primary" disabled={busy || conflict}>
              Сохранить публикацию
            </button>
            <button type="button" onClick={() => edit(null)}>
              Отменить публикацию
            </button>
          </div>
        </form>
      )}
      {!pages.length && !loadError && (
        <p className="service-note">
          Публичных страниц нет. Ничего не опубликовано.
        </p>
      )}
      <div className="publication-pages">
        {pages.map((page) => (
          <article className="group-card" key={page.id}>
            <h3>{page.title}</h3>
            <p>
              {page.enabled ? "Включена" : "Выключена"} ·{" "}
              {page.publications.length} опубликованных сервисов
            </p>
            <a
              href={`${location.protocol}//${location.hostname}:8081/status/${page.slug}`}
              target="_blank"
              rel="noreferrer"
            >
              Открыть публичную страницу ↗
            </a>
            <div className="row-actions">
              <button
                onClick={async () => {
                  try {
                    await navigator.clipboard.writeText(
                      `${location.protocol}//${location.hostname}:8081/status/${page.slug}`,
                    );
                    setError("");
                    setCopied(page.id);
                  } catch {
                    setError(
                      "Не удалось скопировать ссылку. Откройте публичную страницу и скопируйте её адрес.",
                    );
                  }
                }}
              >
                Скопировать публичную ссылку
              </button>
              {copied === page.id && (
                <span role="status">Ссылка скопирована.</span>
              )}
              <button disabled={busy} onClick={() => edit(page)}>
                Изменить публикацию
              </button>
              <button disabled={busy} onClick={() => remove(page)}>
                Удалить страницу
              </button>
            </div>
          </article>
        ))}
      </div>
    </section>
  );
}
