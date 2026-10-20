import { useEffect, useState } from "react";
import { request } from "./api";
type Delivery = {
  id: string;
  event_type: string;
  email: string;
  status: string;
  attempts: number;
  next_attempt_at: string;
  sent_at: string | null;
  last_error: string | null;
};
export function NotificationsPanel({ active }: { active: boolean }) {
  const [data, setData] = useState<{
    items: Delivery[];
    has_more: boolean;
  } | null>(null);
  const [error, setError] = useState("");
  const [offset, setOffset] = useState(0);
  const [refresh, setRefresh] = useState(0);
  useEffect(() => {
    if (!active) return;
    let alive = true;
    const load = () =>
      request<{ items: Delivery[]; has_more: boolean }>(
        `/notifications?limit=50&offset=${offset}`,
      )
        .then((value) => {
          if (alive) {
            setData(value);
            setError("");
          }
        })
        .catch((e) => {
          if (alive) setError(e.message);
        });
    void load();
    const timer = setInterval(load, 10000);
    return () => {
      alive = false;
      clearInterval(timer);
    };
  }, [active, offset, refresh]);
  return (
    <section className="panel" id="notifications">
      <div className="section-heading">
        <div>
          <h2>Notification deliveries</h2>
          <p>Durable email events · SMTP acceptance, not mailbox delivery</p>
        </div>
        <button
          onClick={() => {
            location.hash = "notifications";
            setRefresh((v) => v + 1);
          }}
        >
          Refresh deliveries
        </button>
      </div>
      <p className="service-note">
        Configure recipients in <a href="#groups">Groups</a>. Retries retain the
        same delivery ID.
      </p>
      {error && (
        <p role="alert" className="error">
          {error}
        </p>
      )}
      {active && !data && !error && (
        <p className="service-note">Loading delivery status…</p>
      )}
      {data && (
        <>
          <div
            className="table-scroll"
            tabIndex={0}
            role="region"
            aria-label="Scrollable table"
          >
            <table>
              <thead>
                <tr>
                  <th>Event</th>
                  <th>Recipient</th>
                  <th>Status</th>
                  <th>Attempts</th>
                  <th>Sent / next attempt</th>
                  <th>Diagnostic</th>
                </tr>
              </thead>
              <tbody>
                {data.items.map((d) => (
                  <tr key={d.id}>
                    <td>{d.event_type}</td>
                    <td>{d.email}</td>
                    <td>
                      <span className={`badge ${d.status.toLowerCase()}`}>
                        {d.status === "PENDING" && d.attempts
                          ? "RETRY (PENDING)"
                          : d.status}
                      </span>
                    </td>
                    <td>{d.attempts}</td>
                    <td>
                      {new Date(
                        d.sent_at ?? d.next_attempt_at,
                      ).toLocaleString()}
                    </td>
                    <td>{d.last_error ?? "—"}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
          {!data.items.length && (
            <p className="service-note">No notification deliveries yet.</p>
          )}
          <div className="row-actions pagination">
            <button
              disabled={!offset}
              onClick={() => setOffset(Math.max(0, offset - 50))}
            >
              Previous deliveries
            </button>
            <button
              disabled={!data.has_more}
              onClick={() => setOffset(offset + 50)}
            >
              Next deliveries
            </button>
          </div>
        </>
      )}
    </section>
  );
}
