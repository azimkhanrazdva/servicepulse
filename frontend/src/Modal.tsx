import { useEffect, useRef } from "react";
import type { ReactNode } from "react";
export function Modal({
  children,
  onClose,
  busy = false,
}: {
  children: ReactNode;
  onClose: () => void;
  busy?: boolean;
}) {
  const ref = useRef<HTMLDialogElement>(null);
  useEffect(() => {
    const previous = document.activeElement as HTMLElement | null;
    const dialog = ref.current!;
    if (dialog.showModal) dialog.showModal();
    else dialog.open = true;
    return () => {
      dialog.close?.();
      previous?.focus();
    };
  }, []);
  return (
    <dialog
      ref={ref}
      aria-label="Monitor editor dialog"
      onKeyDown={(event) => {
        if (event.key !== "Tab") return;
        const fields = Array.from(
          event.currentTarget.querySelectorAll<HTMLElement>(
            "button:not(:disabled), input:not(:disabled), select:not(:disabled), textarea:not(:disabled), a[href]",
          ),
        );
        const first = fields[0],
          last = fields.at(-1);
        if (event.shiftKey && document.activeElement === first) {
          event.preventDefault();
          last?.focus();
        } else if (!event.shiftKey && document.activeElement === last) {
          event.preventDefault();
          first?.focus();
        }
      }}
      onCancel={(event) => {
        event.preventDefault();
        if (!busy) onClose();
      }}
    >
      <button
        className="dialog-close"
        aria-label="Close monitor editor"
        disabled={busy}
        onClick={onClose}
      >
        ×
      </button>
      {children}
    </dialog>
  );
}
