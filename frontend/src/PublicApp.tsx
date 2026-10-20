import { useEffect, useState } from "react";
import { AnalyticsPanel } from "./AnalyticsPanel";

type Service = {
  id: string;
  name: string;
  state: string;
  last_checked_at: string | null;
  freshness: string;
  maintenance: boolean;
  show_history: boolean;
};
type Snapshot = { title: string; state: string; services: Service[] };

export function PublicApp() {
  const slug = location.pathname.split("/").filter(Boolean)[1] ?? "";
  const [snapshot, setSnapshot] = useState<Snapshot | null>(null);
  const [connection, setConnection] = useState("Connecting");
  const [error, setError] = useState("");
  const [retry, setRetry] = useState(0);
  useEffect(() => {
    let active = true,
      received = false;
    let stream: EventSource | undefined;
    const base = `/api/public/pages/${encodeURIComponent(slug)}`;
    const connect = () => {
      stream?.close();
      stream = new EventSource(base + "/events");
      stream.addEventListener("status", (event) => {
        if (!active) return;
        try {
          setSnapshot(JSON.parse((event as MessageEvent).data));
          received = true;
          setError("");
          setConnection("Live");
        } catch {
          setError("Status update could not be read.");
        }
      });
      stream.addEventListener("unavailable", () => {
        if (!active) return;
        received = true;
        setSnapshot(null);
        setError("This status page is unavailable.");
        setConnection("Unavailable");
        stream?.close();
      });
      stream.onerror = () => {
        if (active) {
          received = true;
          setSnapshot(null);
          setConnection("Reconnecting");
          setError(
            "Public status connection interrupted. Retry to revalidate the page.",
          );
        }
      };
    };
    fetch(base, { cache: "no-store" })
      .then(async (response) => {
        if (!response.ok)
          throw new Error(
            response.status === 404
              ? "This status page is unavailable."
              : "Could not load public status.",
          );
        return response.json();
      })
      .then((data) => {
        if (active && !received) setSnapshot(data);
      })
      .catch((e) => {
        if (active && !received) {
          setError(e.message);
          setSnapshot(null);
        }
      });
    const offline = () => {
      stream?.close();
      received = true;
      setSnapshot(null);
      setConnection("Reconnecting");
    };
    connect();
    window.addEventListener("offline", offline);
    window.addEventListener("online", connect);
    return () => {
      active = false;
      stream?.close();
      window.removeEventListener("offline", offline);
      window.removeEventListener("online", connect);
    };
  }, [slug, retry]);
  return (
    <main className="public-shell">
      <header className="public-header">
        <span className="brand">
          <span className="brand-icon">ϟ</span> ServicePulse
        </span>
        <span
          className={`connection ${connection === "Live" ? "live" : ""}`}
          role="status"
        >
          ● {connection}
        </span>
      </header>
      <div className="public-intro">
        <div className="eyebrow">SERVICE STATUS / LIVE OBSERVATIONS</div>
        <h1>
          {snapshot?.title ?? "Service status"}
          <span>.</span>
        </h1>
        <p>Current service health, shared by its owner.</p>
      </div>
      {connection === "Reconnecting" && (
        <p className="notice">
          Connection interrupted. Displayed observations may be stale.
        </p>
      )}
      {error && (
        <div className="error" role="alert">
          {error}
          <button onClick={() => setRetry((v) => v + 1)}>Retry status</button>
        </div>
      )}
      {!snapshot && !error && <p>Loading public status…</p>}
      {snapshot && (
        <>
          <div
            className={`public-overall overall-${snapshot.state.toLowerCase()}`}
          >
            <span className={`status ${snapshot.state.toLowerCase()}`}>
              ● {snapshot.state}
            </span>
            <p>
              {snapshot.state === "UP"
                ? "Published services are operational."
                : snapshot.state === "DOWN"
                  ? "A published service has a confirmed incident."
                  : "See individual services for observation coverage."}
            </p>
          </div>
          {!snapshot.services.length && (
            <section className="panel public-empty">
              <h2>No services published</h2>
              <p>The owner has not selected services for this page.</p>
            </section>
          )}
          <div className="public-services">
            {snapshot.services.map((s) => (
              <article
                className="panel public-service"
                key={s.id}
                data-testid={`public-${s.id}`}
              >
                <div className="section-heading">
                  <div>
                    <h2>{s.name}</h2>
                    <p>
                      {s.last_checked_at
                        ? `Last observed ${new Date(s.last_checked_at).toLocaleString()}`
                        : "NO DATA · awaiting first observation"}
                    </p>
                  </div>
                  <span className={`status ${s.state.toLowerCase()}`}>
                    ● {s.state}
                  </span>
                </div>
                {s.freshness === "STALE" && (
                  <p className="service-note">
                    NO RECENT DATA · last known state shown; observation gap is
                    not an outage.
                  </p>
                )}
                {s.maintenance && (
                  <p className="service-note maintenance-badge">
                    Scheduled maintenance · observations continue
                  </p>
                )}
                {s.show_history && (
                  <AnalyticsPanel
                    base={`/api/public/pages/${encodeURIComponent(slug)}/services/${s.id}/analytics`}
                    revision={s.last_checked_at}
                  />
                )}
              </article>
            ))}
          </div>
        </>
      )}
      <footer className="public-footer">
        ServicePulse · Observed, never assumed.
      </footer>
    </main>
  );
}
