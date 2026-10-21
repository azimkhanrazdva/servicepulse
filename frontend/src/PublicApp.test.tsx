import {
  act,
  cleanup,
  fireEvent,
  render,
  screen,
  waitFor,
} from "@testing-library/react";
import { afterEach, beforeEach, expect, it, vi } from "vitest";
import { PublicApp } from "./PublicApp";
class Events {
  static current: Events;
  listeners: Record<string, (event: { data: string }) => void> = {};
  onerror: (() => void) | null = null;
  close = vi.fn();
  constructor() {
    Events.current = this;
  }
  addEventListener(name: string, callback: (event: { data: string }) => void) {
    this.listeners[name] = callback;
  }
  emit(name: string, data: unknown) {
    this.listeners[name]?.({ data: JSON.stringify(data) });
  }
}
const snapshot = {
  title: "Customer health",
  state: "UP",
  services: [
    {
      id: "public-id",
      name: "Customer API",
      state: "UP",
      freshness: "FRESH",
      last_checked_at: "2026-10-19T00:00:00Z",
      maintenance: false,
      show_history: false,
    },
  ],
};
beforeEach(() => {
  history.replaceState(null, "", "/status/customer");
  vi.stubGlobal("EventSource", Events);
});
afterEach(() => {
  cleanup();
  vi.unstubAllGlobals();
  history.replaceState(null, "", "/");
});
it("renders only the public snapshot and clears it on live revocation", async () => {
  vi.stubGlobal(
    "fetch",
    vi.fn().mockResolvedValue({ ok: true, json: async () => snapshot }),
  );
  render(<PublicApp />);
  expect(await screen.findByText("Customer API")).toBeTruthy();
  act(() => Events.current.emit("status", { ...snapshot, services: [] }));
  expect(await screen.findByText("Сервисы не опубликованы")).toBeTruthy();
  expect(screen.queryByText("Customer API")).toBeNull();
  act(() => Events.current.emit("unavailable", {}));
  expect(await screen.findByRole("alert")).toBeTruthy();
});
it("clears received data after disconnection and synchronizes after reconnect", async () => {
  vi.stubGlobal(
    "fetch",
    vi.fn().mockResolvedValue({ ok: true, json: async () => snapshot }),
  );
  render(<PublicApp />);
  await screen.findByText("Customer API");
  const old = Events.current;
  act(() => window.dispatchEvent(new Event("offline")));
  expect(screen.queryByText("Customer API")).toBeNull();
  expect(old.close).toHaveBeenCalled();
  act(() => window.dispatchEvent(new Event("online")));
  expect(Events.current).not.toBe(old);
  act(() => Events.current.emit("status", snapshot));
  expect(await screen.findByText("Customer API")).toBeTruthy();
});
it("does not let a late REST response restore a revoked SSE snapshot", async () => {
  let resolve!: (value: unknown) => void;
  vi.stubGlobal(
    "fetch",
    vi.fn().mockReturnValue(
      new Promise((r) => {
        resolve = r;
      }),
    ),
  );
  render(<PublicApp />);
  act(() => Events.current.emit("unavailable", {}));
  await act(async () => resolve({ ok: true, json: async () => snapshot }));
  await waitFor(() => expect(screen.queryByText("Customer API")).toBeNull());
  expect(screen.getByRole("alert")).toBeTruthy();
});
it("handles missing pages and offers a real retry", async () => {
  const fetcher = vi.fn().mockResolvedValue({ ok: false, status: 404 });
  vi.stubGlobal("fetch", fetcher);
  render(<PublicApp />);
  expect(await screen.findByRole("alert")).toBeTruthy();
  fireEvent.click(screen.getByRole("button", { name: "Повторить загрузку" }));
  await waitFor(() => expect(fetcher).toHaveBeenCalledTimes(2));
});
