import {
  act,
  cleanup,
  fireEvent,
  render,
  screen,
  waitFor,
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
  await screen.findByText("Start with your first service");
  FakeEvents.latest.onmessage?.({ data: JSON.stringify([monitor]) });
  expect(await screen.findByRole("button", { name: "Test API" })).toBeTruthy();
  expect(screen.getByText("● UP")).toBeTruthy();
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
  await screen.findByText("Start with your first service");
  const old = FakeEvents.latest;
  act(() => window.dispatchEvent(new Event("offline")));
  expect(old.close).toHaveBeenCalled();
  expect(screen.getByRole("status").textContent).toBe("● Reconnecting");
  act(() => window.dispatchEvent(new Event("online")));
  expect(FakeEvents.latest).not.toBe(old);
  act(() => FakeEvents.latest.onmessage?.({ data: JSON.stringify([monitor]) }));
  expect(await screen.findByRole("button", { name: "Test API" })).toBeTruthy();
  expect(screen.getByRole("status").textContent).toBe("● Live");
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
  await screen.findByText("Start with your first service");
  fireEvent.click(screen.getByRole("button", { name: "+ Add monitor" }));
  fireEvent.change(screen.getByLabelText("Name"), {
    target: { value: "Test API" },
  });
  fireEvent.change(screen.getByLabelText("URL"), {
    target: { value: "https://example.com" },
  });
  fireEvent.click(screen.getByRole("button", { name: "Create monitor" }));
  await screen.findByRole("button", { name: "Test API" });
  await waitFor(() => expect(fetcher).toHaveBeenCalledTimes(5));
  const posted = fetcher.mock.calls.find((call) => call[1]?.method === "POST")!;
  expect(JSON.parse(posted[1].body)).toMatchObject({
    interval_seconds: 30,
    timeout_seconds: 5,
  });
});
