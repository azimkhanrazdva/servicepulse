import {
  act,
  cleanup,
  render,
  screen,
  waitFor,
  fireEvent,
} from "@testing-library/react";
import { afterEach, expect, it, vi } from "vitest";
import { AnalyticsPanel, ResponseChart } from "./AnalyticsPanel";
import type { Analytics } from "./AnalyticsPanel";
afterEach(() => {
  cleanup();
  vi.unstubAllGlobals();
  vi.useRealTimers();
});

it("advances rolling history even when no new observation arrives", async () => {
  vi.useFakeTimers();
  const fetcher = vi.fn().mockResolvedValue({
    ok: true,
    json: async () => ({ ...empty, uptime_percent: 100 }),
  });
  vi.stubGlobal("fetch", fetcher);
  await act(async () => {
    render(<AnalyticsPanel base="/api/monitors/a/analytics" revision={null} />);
  });
  expect(screen.getAllByText("100.00%")).toHaveLength(3);
  fetcher.mockResolvedValue({ ok: true, json: async () => empty });
  await act(async () => {
    vi.advanceTimersByTime(60000);
  });
  expect(fetcher).toHaveBeenCalledTimes(6);
  expect(screen.queryByText("100.00%")).toBeNull();
});

it("pairs sample uptime with prominent low coverage and a continuity warning", async () => {
  vi.stubGlobal(
    "fetch",
    vi.fn().mockResolvedValue({
      ok: true,
      json: async () => ({
        ...empty,
        uptime_percent: 100,
        coverage_percent: 1,
        samples: 10,
      }),
    }),
  );
  const view = render(
    <AnalyticsPanel base="/api/monitors/a/analytics" revision={null} />,
  );
  await waitFor(() =>
    expect(view.container.querySelectorAll(".coverage-value b")).toHaveLength(
      3,
    ),
  );
  expect(
    [...view.container.querySelectorAll(".coverage-value b")].every(
      (el) => el.textContent === "1.00%",
    ),
  ).toBe(true);
  expect(screen.getByText(/не подтверждает непрерывную работу/)).toBeTruthy();
});
const empty: Analytics = {
  period: "24h",
  start_at: "2026-10-19T00:00:00Z",
  end_at: "2026-10-20T00:00:00Z",
  samples: 0,
  successful: 0,
  uptime_percent: null,
  coverage_percent: 0,
  unobserved_seconds: 86400,
  bucket_seconds: 300,
  status: "NO_DATA",
  buckets: [
    {
      at: "2026-10-19T00:00:00Z",
      samples: 0,
      successful: 0,
      mean_ms: null,
      min_ms: null,
      max_ms: null,
      coverage_percent: 0,
    },
  ],
};
it("shows all three NO DATA summaries without inventing healthy uptime or zero latency", async () => {
  const fetcher = vi
    .fn()
    .mockResolvedValue({ ok: true, json: async () => empty });
  vi.stubGlobal("fetch", fetcher);
  const view = render(
    <AnalyticsPanel base="/api/monitors/a/analytics" revision={null} />,
  );
  await waitFor(() =>
    expect(view.container.querySelectorAll(".uptime-grid strong")).toHaveLength(
      3,
    ),
  );
  expect(
    [...view.container.querySelectorAll(".uptime-grid strong")].map(
      (node) => node.textContent,
    ),
  ).toEqual(["НЕТ ДАННЫХ", "НЕТ ДАННЫХ", "НЕТ ДАННЫХ"]);
  expect(fetcher).toHaveBeenCalledTimes(3);
  expect(screen.queryByText("100.00%")).toBeNull();
  expect(view.container.querySelectorAll("[data-gap]")).toHaveLength(1);
  fireEvent.change(screen.getByLabelText("Период истории"), {
    target: { value: "30d" },
  });
  expect(
    (screen.getByLabelText("Период истории") as HTMLSelectElement).value,
  ).toBe("30d");
});
it("renders a missing bucket as a gap and real zero latency as an observation", () => {
  const observed = {
    ...empty.buckets[0],
    at: "2026-10-19T00:05:00Z",
    samples: 1,
    successful: 1,
    mean_ms: 0,
    min_ms: 0,
    max_ms: 0,
  };
  const view = render(
    <ResponseChart
      data={{ ...empty, buckets: [empty.buckets[0], observed] }}
    />,
  );
  expect(view.container.querySelectorAll("[data-gap]")).toHaveLength(1);
  expect(view.container.querySelectorAll("rect")).toHaveLength(2);
  expect(screen.getByRole("img").textContent).toContain("0.0 мс");
});
it("removes old aggregates on permission failure", async () => {
  const fetcher = vi.fn().mockResolvedValue({
    ok: true,
    json: async () => ({ ...empty, uptime_percent: 100 }),
  });
  vi.stubGlobal("fetch", fetcher);
  const view = render(
    <AnalyticsPanel base="/api/public/example/analytics" revision="one" />,
  );
  await waitFor(() => expect(screen.getAllByText("100.00%")).toHaveLength(3));
  fetcher.mockResolvedValue({ ok: false });
  view.rerender(
    <AnalyticsPanel base="/api/public/example/analytics" revision="two" />,
  );
  expect(await screen.findByRole("alert")).toBeTruthy();
  expect(screen.queryByText("100.00%")).toBeNull();
});
