import {
  act,
  cleanup,
  fireEvent,
  render,
  screen,
} from "@testing-library/react";
import { afterEach, expect, it, vi } from "vitest";
import { IncidentsPanel } from "./IncidentsPanel";

afterEach(() => {
  cleanup();
  vi.useRealTimers();
  vi.unstubAllGlobals();
});
const incident = {
  id: "one",
  monitor_id: "m",
  monitor_name: "Failing API",
  opened_at: "2026-10-19T12:00:00Z",
  recovered_at: null,
  closed_at: null,
  closure_reason: null,
  state: "OPEN",
};

it("updates duration on a clock and refreshes administrative closure on SSE revision", async () => {
  vi.useFakeTimers({ shouldAdvanceTime: true });
  vi.setSystemTime(new Date("2026-10-19T12:00:05Z"));
  vi.stubGlobal(
    "fetch",
    vi.fn().mockResolvedValue({
      ok: true,
      json: async () => ({ items: [incident], has_more: false }),
    }),
  );
  const view = render(<IncidentsPanel monitors={[]} revision={0} />);
  await screen.findByText("Failing API");
  act(() => {
    vi.advanceTimersByTime(1000);
  });
  expect(screen.getByTestId("incident-duration").textContent).toBe("6с");
  vi.useRealTimers();
  vi.stubGlobal(
    "fetch",
    vi.fn().mockResolvedValue({
      ok: true,
      json: async () => ({
        items: [
          {
            ...incident,
            closed_at: "2026-10-19T12:00:08Z",
            closure_reason: "PAUSED",
            state: "CLOSED",
          },
        ],
        has_more: false,
      }),
    }),
  );
  view.rerender(<IncidentsPanel monitors={[]} revision={1} />);
  await screen.findByText("Закрыт (CLOSED)");
  expect(screen.getByTestId("incident-duration").textContent).toBe("8с");
  expect(screen.getByText(/PAUSED/)).toBeTruthy();
});

it("filters and paginates the real API and shows failures", async () => {
  const fetcher = vi.fn().mockResolvedValue({
    ok: true,
    json: async () => ({ items: [], has_more: true }),
  });
  vi.stubGlobal("fetch", fetcher);
  render(<IncidentsPanel monitors={[]} revision={0} />);
  await screen.findByText("Нет инцидентов с выбранными параметрами.");
  fireEvent.click(screen.getByRole("button", { name: "Следующие инциденты" }));
  await screen.findByText("Страница 2");
  expect(fetcher.mock.calls.at(-1)?.[0]).toContain("offset=20");
  fireEvent.change(screen.getByLabelText("Состояние инцидента"), {
    target: { value: "OPEN" },
  });
  await screen.findByText("Страница 1");
  expect(fetcher.mock.calls.at(-1)?.[0]).toContain("state=OPEN");
  fetcher.mockRejectedValue(new Error("Недоступно"));
  fireEvent.change(screen.getByLabelText("Состояние инцидента"), {
    target: { value: "CLOSED" },
  });
  expect((await screen.findByRole("alert")).textContent).toContain(
    "Недоступно",
  );
});
