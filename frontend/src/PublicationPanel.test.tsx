import {
  cleanup,
  fireEvent,
  render,
  screen,
  waitFor,
} from "@testing-library/react";
import { afterEach, expect, it, vi } from "vitest";
import { PublicationPanel } from "./PublicationPanel";
import type { Monitor } from "./api";
afterEach(() => {
  cleanup();
  vi.unstubAllGlobals();
});
const monitor: Monitor = {
  id: "internal",
  name: "Internal API",
  url: "http://example.com",
  interval_seconds: 30,
  timeout_seconds: 5,
  expected_status: 200,
  expected_body: null,
  failure_threshold: 2,
  state: "UP",
  config_version: 1,
  run_requested: false,
  is_running: false,
  last_status_code: 200,
  last_response_ms: 1,
  last_checked_at: null,
  consecutive_failures: 0,
};
it("does not implicitly publish monitors or enable a new page", async () => {
  const fetcher = vi.fn().mockResolvedValue({ ok: true, json: async () => [] });
  vi.stubGlobal("fetch", fetcher);
  render(<PublicationPanel monitors={[monitor]} />);
  fireEvent.click(screen.getByRole("button", { name: "+ Создать страницу" }));
  fireEvent.change(screen.getByLabelText("Заголовок публичной страницы"), {
    target: { value: "Customer" },
  });
  fireEvent.change(screen.getByLabelText("Адрес страницы (slug)"), {
    target: { value: "customer" },
  });
  expect(
    (
      screen.getByLabelText(
        "Разрешить публичный доступ к странице",
      ) as HTMLInputElement
    ).checked,
  ).toBe(false);
  expect(
    (
      screen.getByLabelText("Опубликовать Internal API", {
        exact: true,
      }) as HTMLInputElement
    ).checked,
  ).toBe(false);
  fireEvent.click(screen.getByRole("button", { name: "Сохранить публикацию" }));
  await waitFor(() =>
    expect(fetcher.mock.calls.some((call) => call[1]?.method === "POST")).toBe(
      true,
    ),
  );
  const sent = fetcher.mock.calls.find((call) => call[1]?.method === "POST")!;
  expect(JSON.parse(sent[1].body)).toEqual({
    slug: "customer",
    title: "Customer",
    enabled: false,
    publications: [],
  });
});
it("preserves the public-label draft on an optimistic concurrency conflict", async () => {
  const page = {
    id: "page",
    slug: "customer",
    title: "Customer",
    enabled: true,
    config_version: 3,
    publications: [
      {
        id: "public-id",
        monitor_id: "internal",
        public_name: "Customer API",
        show_history: false,
      },
    ],
  };
  const fetcher = vi.fn().mockImplementation((_path, options) =>
    Promise.resolve(
      options?.method === "PUT"
        ? {
            ok: false,
            status: 409,
            json: async () => ({ detail: "Configuration changed" }),
          }
        : { ok: true, json: async () => [page] },
    ),
  );
  vi.stubGlobal("fetch", fetcher);
  render(<PublicationPanel monitors={[monitor]} />);
  fireEvent.click(
    await screen.findByRole("button", { name: "Изменить публикацию" }),
  );
  fireEvent.change(
    screen.getByLabelText("Публичное название для Internal API"),
    {
      target: { value: "Preserved customer label" },
    },
  );
  fireEvent.click(screen.getByRole("button", { name: "Сохранить публикацию" }));
  expect(
    await screen.findByText(/Ваш черновик публикации сохранён/),
  ).toBeTruthy();
  expect(
    (
      screen.getByLabelText(
        "Публичное название для Internal API",
      ) as HTMLInputElement
    ).value,
  ).toBe("Preserved customer label");
  expect(
    (
      screen.getByRole("button", {
        name: "Сохранить публикацию",
      }) as HTMLButtonElement
    ).disabled,
  ).toBe(true);
  expect(
    JSON.parse(
      fetcher.mock.calls.find((call) => call[1]?.method === "PUT")![1].body,
    ).config_version,
  ).toBe(3);
});
