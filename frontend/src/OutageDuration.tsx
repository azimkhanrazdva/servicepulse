import { useEffect, useState } from "react";
export function OutageDuration({ started }: { started: string | undefined }) {
  const [clock, setClock] = useState(Date.now());
  useEffect(() => {
    if (!started) return;
    const timer = setInterval(() => setClock(Date.now()), 1000);
    return () => clearInterval(timer);
  }, [started]);
  if (!started) return <>Ожидание данных инцидента</>;
  const seconds = Math.max(
    0,
    Math.floor((clock - new Date(started).getTime()) / 1000),
  );
  return (
    <span title={`Подтверждено в ${new Date(started).toLocaleString("ru-RU")}`}>
      {Math.floor(seconds / 3600)}ч {Math.floor((seconds % 3600) / 60)}мин{" "}
      {seconds % 60}с
    </span>
  );
}
