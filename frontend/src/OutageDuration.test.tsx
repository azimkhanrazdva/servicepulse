import { act, cleanup, render, screen } from "@testing-library/react";
import { afterEach, expect, it, vi } from "vitest";
import { OutageDuration } from "./OutageDuration";
afterEach(() => {
  cleanup();
  vi.useRealTimers();
});
it("ticks from the persisted incident start and never invents a start when unavailable", () => {
  vi.useFakeTimers();
  vi.setSystemTime(new Date("2026-10-20T00:01:05Z"));
  const view = render(<OutageDuration started="2026-10-20T00:00:00Z" />);
  expect(screen.getByText("0ч 1мин 5с")).toBeTruthy();
  act(() => vi.advanceTimersByTime(1000));
  expect(screen.getByText("0ч 1мин 6с")).toBeTruthy();
  view.rerender(<OutageDuration started={undefined} />);
  expect(screen.getByText("Ожидание данных инцидента")).toBeTruthy();
});
