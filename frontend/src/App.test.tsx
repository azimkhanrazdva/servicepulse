import {
  act,
  cleanup,
  fireEvent,
  render,
  screen,
  waitFor,
  within,
} from "@testing-library/react";
import { afterEach, beforeEach, expect, it, vi } from "vitest";
import { App } from "./App";

class FakeEvents {
  static latest: FakeEvents;
  addEventListener = vi.fn();
  onopen: (() => void) | null = null;
  onmessage: ((event: { data: string }) => void) | null = null;
  onerror: (() => void) | null = null;
  close = vi.fn();
  constructor() {
    FakeEvents.latest = this;
  }
}
const monitor = {
  id: "a",
  name: "Test API",
  url: "https://example.com",
  state: "UP",
  interval_seconds: 30,
  timeout_seconds: 5,
  last_status_code: 200,
  last_response_ms: 12,
  last_checked_at: "2026-10-19T10:00:00Z",
  consecutive_failures: 0,
  config_version: 1,
  expected_status: 200,
  expected_body: null,
  failure_threshold: 2,
  run_requested: false,
  is_running: false,
};

beforeEach(() => {
  window.history.replaceState({}, "", "/");
  vi.stubGlobal("EventSource", FakeEvents);
});
afterEach(() => {
  cleanup();
  vi.unstubAllGlobals();
});

it("renders empty state then accepts an SSE snapshot", async () => {
  vi.stubGlobal(
    "fetch",
    vi.fn().mockResolvedValue({ ok: true, json: async () => [] }),
  );
  render(<App />);
  await screen.findByText("Добавьте первый сервис");
  FakeEvents.latest.onmessage?.({ data: JSON.stringify([monitor]) });
  expect(await screen.findByRole("button", { name: "Test API" })).toBeTruthy();
  expect(screen.getByText("● Доступен (UP)")).toBeTruthy();
});

it("shows an API error", async () => {
  vi.stubGlobal("fetch", vi.fn().mockRejectedValue(new Error("Offline")));
  render(<App />);
  expect((await screen.findAllByRole("alert"))[0]).toHaveProperty(
    "textContent",
    "Offline×",
  );
});

it("reconnects and receives a full snapshot after browser network loss", async () => {
  vi.stubGlobal(
    "fetch",
    vi.fn().mockResolvedValue({ ok: true, json: async () => [] }),
  );
  render(<App />);
  await screen.findByText("Добавьте первый сервис");
  const old = FakeEvents.latest;
  act(() => window.dispatchEvent(new Event("offline")));
  expect(old.close).toHaveBeenCalled();
  expect(screen.getByRole("status").textContent).toBe("● Переподключение");
  act(() => window.dispatchEvent(new Event("online")));
  expect(FakeEvents.latest).not.toBe(old);
  act(() => FakeEvents.latest.onmessage?.({ data: JSON.stringify([monitor]) }));
  expect(await screen.findByRole("button", { name: "Test API" })).toBeTruthy();
  expect(screen.getByRole("status").textContent).toBe("● На связи");
});

it("creates a monitor using real form values", async () => {
  const fetcher = vi.fn().mockImplementation((_url, options) =>
    Promise.resolve({
      ok: true,
      json: async () => (options?.method === "POST" ? monitor : []),
    }),
  );
  vi.stubGlobal("fetch", fetcher);
  render(<App />);
  await screen.findByText("Добавьте первый сервис");
  fireEvent.click(screen.getByRole("button", { name: "+ Добавить монитор" }));
  fireEvent.change(screen.getByLabelText("Название"), {
    target: { value: "Test API" },
  });
  fireEvent.change(screen.getByLabelText("URL"), {
    target: { value: "https://example.com" },
  });
  fireEvent.click(screen.getByRole("button", { name: "Создать монитор" }));
  await screen.findByRole("button", { name: "Test API" });
  // Publication settings and dashboard aggregates add two GETs; POST is still checked below.
  await waitFor(() => expect(fetcher).toHaveBeenCalledTimes(7));
  const posted = fetcher.mock.calls.find((call) => call[1]?.method === "POST")!;
  expect(JSON.parse(posted[1].body)).toMatchObject({
    interval_seconds: 30,
    timeout_seconds: 5,
  });
});

it("tracks anchor navigation and filters only the disclosed loaded selection", async () => {
  vi.stubGlobal(
    "fetch",
    vi.fn().mockResolvedValue({ ok: true, json: async () => [] }),
  );
  render(<App />);
  await screen.findByText("Добавьте первый сервис");
  act(() =>
    FakeEvents.latest.onmessage?.({
      data: JSON.stringify([
        monitor,
        { ...monitor, id: "b", name: "Other", state: "DOWN" },
      ]),
    }),
  );
  expect(screen.getByText(/лимит API: 500/)).toBeTruthy();
  fireEvent.change(screen.getByLabelText("Поиск мониторов"), {
    target: { value: "Other" },
  });
  expect(screen.queryByRole("button", { name: "Test API" })).toBeNull();
  expect(screen.getByRole("button", { name: "Other" })).toBeTruthy();
  act(() => {
    location.hash = "groups";
    window.dispatchEvent(new HashChangeEvent("hashchange"));
  });
  expect(
    within(screen.getByRole("navigation"))
      .getByRole("link", { name: "Группы" })
      .getAttribute("aria-current"),
  ).toBe("page");
  expect(
    screen.getByRole("link", { name: "Обзор" }).getAttribute("aria-current"),
  ).toBeNull();
});

it("keeps the editor open during an outstanding save and closes after success", async () => {
  let finish!: (value: unknown) => void;
  vi.stubGlobal(
    "fetch",
    vi.fn().mockImplementation((_url, options) =>
      options?.method === "POST"
        ? new Promise((resolve) => {
            finish = resolve;
          })
        : Promise.resolve({ ok: true, json: async () => [] }),
    ),
  );
  render(<App />);
  await screen.findByText("Добавьте первый сервис");
  fireEvent.click(screen.getByRole("button", { name: "+ Добавить монитор" }));
  fireEvent.change(screen.getByLabelText("Название"), {
    target: { value: "Slow save" },
  });
  fireEvent.change(screen.getByLabelText("URL"), {
    target: { value: "https://example.com" },
  });
  fireEvent.click(screen.getByRole("button", { name: "Создать монитор" }));
  expect(
    screen
      .getByRole("button", { name: "Закрыть настройку монитора" })
      .hasAttribute("disabled"),
  ).toBe(true);
  fireEvent(
    screen.getByRole("dialog"),
    new Event("cancel", { bubbles: true, cancelable: true }),
  );
  expect(screen.getByRole("dialog")).toBeTruthy();
  await act(async () => finish({ ok: true, json: async () => monitor }));
  await waitFor(() => expect(screen.queryByRole("dialog")).toBeNull());
});
