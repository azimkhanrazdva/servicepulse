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
        aria-label="Response time chart with observation gaps"
      >
        <title>
          Mean response time per bucket; empty buckets are gaps, not zero
          latency.
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
              <title>{new Date(bucket.at).toLocaleString()}: NO DATA</title>
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
                {new Date(bucket.at).toLocaleString()}:{" "}
                {bucket.mean_ms.toFixed(1)} ms · {bucket.samples} observations ·{" "}
                {bucket.coverage_percent.toFixed(1)}% coverage
              </title>
            </rect>
          ),
        )}
      </svg>
      <div className="chart-axis">
        <span>{new Date(data.start_at).toLocaleString()}</span>
        <span>0–{Math.round(max)} ms · bucket means</span>
        <span>{new Date(data.end_at).toLocaleString()}</span>
      </div>
      <p className="subtle">
        Bars are observed bucket means. Gray marks are NO DATA; bars never
        bridge missing observations.
      </p>
      <details className="bucket-data">
        <summary>Inspect aggregated observations</summary>
        <div
          className="table-scroll"
          tabIndex={0}
          role="region"
          aria-label="Scrollable table"
        >
          <table>
            <thead>
              <tr>
                <th>Bucket start</th>
                <th>Checks</th>
                <th>Mean latency</th>
                <th>Coverage</th>
              </tr>
            </thead>
            <tbody>
              {data.buckets.map((b) => (
                <tr key={b.at}>
                  <td>{new Date(b.at).toLocaleString()}</td>
                  <td>{b.samples}</td>
                  <td>
                    {b.mean_ms === null
                      ? "NO DATA"
                      : `${b.mean_ms.toFixed(1)} ms`}
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
              "History is unavailable. Permission or connection may have changed.",
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
    <div className="analytics" aria-label="Availability analytics">
      <div className="section-heading">
        <div>
          <h3>Observed availability</h3>
          <p>Sample-based uptime · coverage reported separately</p>
        </div>
        <label>
          History period{" "}
          <select value={period} onChange={(e) => setPeriod(e.target.value)}>
            <option value="24h">24 hours</option>
            <option value="7d">7 days</option>
            <option value="30d">30 days</option>
          </select>
        </label>
      </div>
      {error ? (
        <p role="alert" className="error">
          {error}
        </p>
      ) : !windows ? (
        <p>Loading observed history…</p>
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
                <span>{p} availability</span>
                <strong>
                  {windows[p].uptime_percent === null
                    ? "NO DATA"
                    : `${windows[p].uptime_percent.toFixed(2)}%`}
                </strong>
                <div className="coverage-value">
                  <span>Observed coverage</span>
                  <b>{windows[p].coverage_percent.toFixed(2)}%</b>
                </div>
                <small>
                  {windows[p].samples} checks ·{" "}
                  {windows[p].coverage_percent.toFixed(2)}% observed coverage
                </small>
              </article>
            ))}
          </div>
          {windows[period].coverage_percent < 90 && (
            <p className="coverage-warning">
              Limited coverage: uptime describes observed checks only, not
              continuous availability.
            </p>
          )}
          <ResponseChart data={windows[period]} />
          <p className="subtle">
            Uptime = successful / observed checks, including maintenance and
            configuration changes. Missing time is not DOWN. Coverage uses
            captured check intervals; legacy observations have no inferred
            coverage.
          </p>
        </>
      )}
    </div>
  );
}
