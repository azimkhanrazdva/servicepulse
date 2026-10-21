import { statusLabel, reasonLabel } from "./ru";
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
          <h2>Доставка уведомлений</h2>
          <p>
            Сохранённые почтовые события · подтверждение SMTP не гарантирует
            получение письма
          </p>
        </div>
        <button
          onClick={() => {
            location.hash = "notifications";
            setRefresh((v) => v + 1);
          }}
        >
          Обновить доставки
        </button>
      </div>
      <p className="service-note">
        Настройте получателей в разделе <a href="#groups">Группы</a>. Повторные
        попытки сохраняют тот же ID доставки.
      </p>
      {error && (
        <p role="alert" className="error">
          {error}
        </p>
      )}
      {active && !data && !error && (
        <p className="service-note">Загрузка состояния доставки…</p>
      )}
      {data && (
        <>
          <div
            className="table-scroll"
            tabIndex={0}
            role="region"
            aria-label="Таблица с прокруткой"
          >
            <table>
              <thead>
                <tr>
                  <th>Событие</th>
                  <th>Получатель</th>
                  <th>Статус</th>
                  <th>Попытки</th>
                  <th>Отправлено / следующая попытка</th>
                  <th>Диагностика</th>
                </tr>
              </thead>
              <tbody>
                {data.items.map((d) => (
                  <tr key={d.id}>
                    <td>
                      {d.event_type === "DOWN"
                        ? "Падение (DOWN)"
                        : statusLabel(d.event_type)}
                    </td>
                    <td>{d.email}</td>
                    <td>
                      <span className={`badge ${d.status.toLowerCase()}`}>
                        {d.status === "PENDING" && d.attempts
                          ? "Повторная попытка (PENDING)"
                          : statusLabel(d.status)}
                      </span>
                    </td>
                    <td>{d.attempts}</td>
                    <td>
                      {new Date(d.sent_at ?? d.next_attempt_at).toLocaleString(
                        "ru-RU",
                      )}
                    </td>
                    <td>{reasonLabel(d.last_error)}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
          {!data.items.length && (
            <p className="service-note">Доставок уведомлений пока нет.</p>
          )}
          <div className="row-actions pagination">
            <button
              disabled={!offset}
              onClick={() => setOffset(Math.max(0, offset - 50))}
            >
              Предыдущие доставки
            </button>
            <button
              disabled={!data.has_more}
              onClick={() => setOffset(offset + 50)}
            >
              Следующие доставки
            </button>
          </div>
        </>
      )}
    </section>
  );
}
