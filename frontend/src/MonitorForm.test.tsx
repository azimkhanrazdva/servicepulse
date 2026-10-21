import { cleanup, fireEvent, render, screen } from "@testing-library/react";
import { afterEach, expect, it, vi } from "vitest";
import { MonitorForm } from "./MonitorForm";
import type { Monitor } from "./api";

const monitor: Monitor = {
  id: "a",
  name: "API",
  url: "https://example.com",
  interval_seconds: 30,
  timeout_seconds: 5,
  expected_status: 200,
  expected_body: null,
  failure_threshold: 2,
  config_version: 1,
  state: "UP",
  consecutive_failures: 0,
  last_status_code: 200,
  last_response_ms: 10,
  last_checked_at: null,
  is_running: false,
  run_requested: false,
};
afterEach(() => {
  cleanup();
  vi.unstubAllGlobals();
});

it("sends editable settings and the version captured when the editor opened", async () => {
  const saved = vi.fn();
  const fetcher = vi.fn().mockResolvedValue({
    ok: true,
    json: async () => ({ ...monitor, config_version: 2 }),
  });
  vi.stubGlobal("fetch", fetcher);
  render(<MonitorForm initial={monitor} onSaved={saved} onCancel={() => {}} />);
  fireEvent.change(screen.getByLabelText("Название"), {
    target: { value: "New API" },
  });
  fireEvent.change(screen.getByLabelText("Ожидаемый текст (необязательно)"), {
    target: { value: "  exact  " },
  });
  fireEvent.click(screen.getByRole("button", { name: "Сохранить монитор" }));
  await screen.findByRole("button", { name: "Сохранить монитор" });
  expect(saved).toHaveBeenCalled();
  expect(JSON.parse(fetcher.mock.calls[0][1].body)).toMatchObject({
    config_version: 1,
    name: "New API",
    expected_body: "  exact  ",
  });
});

it("keeps a conflicted draft until the user explicitly reloads it", async () => {
  vi.stubGlobal(
    "fetch",
    vi
      .fn()
      .mockResolvedValueOnce({
        ok: false,
        status: 409,
        json: async () => ({
          detail: "Configuration changed in another client.",
        }),
      })
      .mockResolvedValueOnce({
        ok: true,
        json: async () => ({
          ...monitor,
          name: "Other client",
          config_version: 2,
        }),
      }),
  );
  render(
    <MonitorForm initial={monitor} onSaved={() => {}} onCancel={() => {}} />,
  );
  fireEvent.change(screen.getByLabelText("Название"), {
    target: { value: "My draft" },
  });
  fireEvent.click(screen.getByRole("button", { name: "Сохранить монитор" }));
  expect(await screen.findByRole("alert")).toHaveProperty(
    "textContent",
    "Данные изменились или операция уже выполняется. Обновите данные перед повторной попыткой; черновик сохранён.",
  );
  expect(screen.getByLabelText("Название")).toHaveProperty("value", "My draft");
  fireEvent.click(
    screen.getByRole("button", {
      name: "Отменить черновик и загрузить заново",
    }),
  );
  expect(await screen.findByDisplayValue("Other client")).toBeTruthy();
});

it("renders useful field validation errors from FastAPI", async () => {
  vi.stubGlobal(
    "fetch",
    vi.fn().mockResolvedValue({
      ok: false,
      status: 422,
      json: async () => ({
        detail: [{ loc: ["body", "url"], msg: "Invalid HTTP(S) target" }],
      }),
    }),
  );
  render(
    <MonitorForm initial={monitor} onSaved={() => {}} onCancel={() => {}} />,
  );
  fireEvent.click(screen.getByRole("button", { name: "Сохранить монитор" }));
  expect(await screen.findByRole("alert")).toHaveProperty(
    "textContent",
    "URL: Недопустимое значение",
  );
});
