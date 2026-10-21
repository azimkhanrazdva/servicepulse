import { afterEach, expect, it, vi } from "vitest";
import { withDeadline } from "./network";
afterEach(() => vi.useRealTimers());
it("times out even when a transport or response body ignores cancellation", async () => {
  vi.useFakeTimers();
  let signal: AbortSignal | undefined;
  const result = withDeadline((s) => {
    signal = s;
    return new Promise(() => {});
  });
  const assertion = expect(result).rejects.toThrow("Время ожидания истекло");
  await vi.advanceTimersByTimeAsync(15000);
  await assertion;
  expect(signal?.aborted).toBe(true);
});
it("cancels a superseded request and clears its deadline", async () => {
  vi.useFakeTimers();
  const controller = new AbortController();
  const result = withDeadline(() => new Promise(() => {}), controller.signal);
  const assertion = expect(result).rejects.toHaveProperty("name", "AbortError");
  controller.abort();
  await assertion;
  expect(vi.getTimerCount()).toBe(0);
});
