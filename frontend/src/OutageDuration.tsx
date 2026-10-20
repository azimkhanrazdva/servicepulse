import { useEffect, useState } from "react";
export function OutageDuration({ started }: { started: string | undefined }) {
  const [clock, setClock] = useState(Date.now());
  useEffect(() => {
    if (!started) return;
    const timer = setInterval(() => setClock(Date.now()), 1000);
    return () => clearInterval(timer);
  }, [started]);
  if (!started) return <>Awaiting incident snapshot</>;
  const seconds = Math.max(
    0,
    Math.floor((clock - new Date(started).getTime()) / 1000),
  );
  return (
    <span title={`Confirmed at ${new Date(started).toLocaleString()}`}>
      {Math.floor(seconds / 3600)}h {Math.floor((seconds % 3600) / 60)}m{" "}
      {seconds % 60}s
    </span>
  );
}
