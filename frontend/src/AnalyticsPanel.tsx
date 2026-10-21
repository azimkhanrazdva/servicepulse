import { periodLabel } from "./ru";
import { useEffect, useState } from "react";
import { withDeadline } from "./network";

export type Bucket = {
  at: string;
  samples: number;
  successful: number;
  mean_ms: number | null;
  min_ms: number | null;
  max_ms: number | null;
  coverage_percent: number;
};
export type Analytics = {
  period: string;
  start_at: string;
  end_at: string;
  samples: number;
  successful: number;
  uptime_percent: number | null;
  coverage_percent: number;
  unobserved_seconds: number;
  bucket_seconds: number;
  status: string;
  buckets: Bucket[];
};

export function ResponseChart({ data }: { data: Analytics }) {
  const max = Math.max(1, ...data.buckets.map((b) => b.mean_ms ?? 0));
  const width = 900,
    height = 150,
    step = width / data.buckets.length;
  return (
    <>
      <svg
        className="response-chart"
        viewBox={`0 0 ${width} ${height + 24}`}
        role="img"
        aria-label="График времени ответа с пропусками наблюдений"
      >
        <title>
          Среднее время ответа за интервал; пустые интервалы означают отсутствие
          наблюдений, а не нулевую задержку.
        </title>
        <line x1="0" x2={width} y1={height} y2={height} stroke="#a3a3a3" />
        {data.buckets.map((bucket, i) =>
          bucket.mean_ms === null ? (
            <rect
              key={bucket.at}
              data-gap="true"
              x={i * step}
              y={height + 6}
              width={Math.max(1, step - 0.5)}
              height="8"
              fill="#bdbdbd"
            >
              <title>
                {new Date(bucket.at).toLocaleString("ru-RU")}: НЕТ ДАННЫХ
              </title>
            </rect>
          ) : (
            <rect
              key={bucket.at}
              x={i * step}
              y={height - Math.max(2, (bucket.mean_ms / max) * (height - 12))}
              width={Math.max(1, step - 0.5)}
              height={Math.max(2, (bucket.mean_ms / max) * (height - 12))}
              fill="#171717"
            >
              <title>
                {new Date(bucket.at).toLocaleString("ru-RU")}:{" "}
                {bucket.mean_ms.toFixed(1)} мс · {bucket.samples} наблюдений ·{" "}
                {bucket.coverage_percent.toFixed(1)}% покрытия
              </title>
            </rect>
          ),
        )}
      </svg>
      <div className="chart-axis">
        <span>{new Date(data.start_at).toLocaleString("ru-RU")}</span>
        <span>0–{Math.round(max)} мс · средние по интервалам</span>
        <span>{new Date(data.end_at).toLocaleString("ru-RU")}</span>
      </div>
      <p className="subtle">
        Столбцы показывают средние значения наблюдений. Серые отметки означают
        отсутствие данных; пропуски не соединяются.
      </p>
      <details className="bucket-data">
        <summary>Просмотреть агрегированные наблюдения</summary>
        <div
          className="table-scroll"
          tabIndex={0}
          role="region"
          aria-label="Таблица с прокруткой"
        >
          <table>
            <thead>
              <tr>
                <th>Начало интервала</th>
                <th>Проверки</th>
                <th>Среднее время ответа</th>
                <th>Покрытие</th>
              </tr>
            </thead>
            <tbody>
              {data.buckets.map((b) => (
                <tr key={b.at}>
                  <td>{new Date(b.at).toLocaleString("ru-RU")}</td>
                  <td>{b.samples}</td>
                  <td>
                    {b.mean_ms === null
                      ? "НЕТ ДАННЫХ"
                      : `${b.mean_ms.toFixed(1)} мс`}
                  </td>
                  <td>{b.coverage_percent.toFixed(1)}%</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </details>
    </>
  );
}

export function AnalyticsPanel({
  base,
  revision,
}: {
  base: string;
  revision: string | null | undefined;
}) {
  const [windows, setWindows] = useState<Record<string, Analytics> | null>(
    null,
  );
  const [period, setPeriod] = useState("24h");
  const [error, setError] = useState("");
  const [refresh, setRefresh] = useState(0);
  useEffect(() => {
    const advance = () => setRefresh((value) => value + 1);
    const timer = setInterval(advance, 60000);
    window.addEventListener("online", advance);
    return () => {
      clearInterval(timer);
      window.removeEventListener("online", advance);
    };
  }, []);
  useEffect(() => {
    const controller = new AbortController();
    setError("");
    setWindows(null);
    Promise.all(
      ["24h", "7d", "30d"].map((value) =>
        withDeadline(async (signal) => {
          const response = await fetch(`${base}?period=${value}`, {
            signal,
            cache: "no-store",
          });
          if (!response.ok)
            throw new Error(
              "История недоступна. Возможно, изменились разрешения или соединение.",
            );
          return [value, await response.json()] as const;
        }, controller.signal),
      ),
    )
      .then((rows) => {
        if (!controller.signal.aborted) setWindows(Object.fromEntries(rows));
      })
      .catch((e) => {
        if (!controller.signal.aborted) setError((e as Error).message);
      });
    return () => controller.abort();
  }, [base, revision, refresh]);
  return (
    <div className="analytics" aria-label="Аналитика доступности">
      <div className="section-heading">
        <div>
          <h3>Наблюдаемая доступность</h3>
          <p>Доступность по проверкам · покрытие времени показано отдельно</p>
        </div>
        <label>
          Период истории{" "}
          <select value={period} onChange={(e) => setPeriod(e.target.value)}>
            <option value="24h">24 часа</option>
            <option value="7d">7 дней</option>
            <option value="30d">30 дней</option>
          </select>
        </label>
      </div>
      {error ? (
        <p role="alert" className="error">
          {error}
        </p>
      ) : !windows ? (
        <p>Загрузка истории наблюдений…</p>
      ) : (
        <>
          <div className="uptime-grid">
            {["24h", "7d", "30d"].map((p) => (
              <article
                key={p}
                className={
                  windows[p].coverage_percent < 90 ? "low-coverage" : ""
                }
              >
                <span>{periodLabel(p)} · доступность</span>
                <strong>
                  {windows[p].uptime_percent === null
                    ? "НЕТ ДАННЫХ"
                    : `${windows[p].uptime_percent.toFixed(2)}%`}
                </strong>
                <div className="coverage-value">
                  <span>Покрытие наблюдениями</span>
                  <b>{windows[p].coverage_percent.toFixed(2)}%</b>
                </div>
                <small>
                  {windows[p].samples} проверок ·{" "}
                  {windows[p].coverage_percent.toFixed(2)}% покрытия
                  наблюдениями
                </small>
              </article>
            ))}
          </div>
          {windows[period].coverage_percent < 90 && (
            <p className="coverage-warning">
              Низкое покрытие: доступность рассчитана только по выполненным
              проверкам и не подтверждает непрерывную работу.
            </p>
          )}
          <ResponseChart data={windows[period]} />
          <p className="subtle">
            Доступность = успешные / выполненные проверки, включая обслуживание
            и изменения настроек. Пропуски не считаются падением. Покрытие
            учитывает сохранённые интервалы проверок; для старых наблюдений
            неизвестное покрытие не восстанавливается.
          </p>
        </>
      )}
    </div>
  );
}
