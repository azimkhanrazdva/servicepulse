import {
  cleanup,
  fireEvent,
  render,
  screen,
  waitFor,
} from "@testing-library/react";
import { afterEach, expect, it, vi } from "vitest";
import { MaintenancePanel } from "./MaintenancePanel";
import type { Group } from "./api";

afterEach(() => {
  cleanup();
  vi.unstubAllGlobals();
});
const page = {
  items: [],
  has_more: false,
  active_monitor_ids: [],
  active_group_ids: [],
};
const groups: Group[] = [
  {
    id: "g",
    name: "Ops",
    config_version: 1,
    monitor_ids: [],
    recipients: ["ops@example.com"],
    state: "UNKNOWN",
  },
];

it("clears a transient refresh error after reconnect without clearing mutation drafts", async () => {
  const fetcher = vi
    .fn()
    .mockRejectedValueOnce(new Error("Offline"))
    .mockResolvedValue({ ok: true, json: async () => page });
  vi.stubGlobal("fetch", fetcher);
  const onSnapshot = vi.fn();
  const view = render(
    <MaintenancePanel
      revision={0}
      monitors={[]}
      groups={groups}
      onSnapshot={onSnapshot}
    />,
  );
  expect((await screen.findByRole("alert")).textContent).toContain("Offline");
  view.rerender(
    <MaintenancePanel
      revision={1}
      monitors={[]}
      groups={groups}
      onSnapshot={onSnapshot}
    />,
  );
  await waitFor(() => expect(screen.queryByRole("alert")).toBeNull());
});

it("creates a group window with explicit UTC dates", async () => {
  const fetcher = vi
    .fn()
    .mockResolvedValue({ ok: true, json: async () => page });
  vi.stubGlobal("fetch", fetcher);
  render(
    <MaintenancePanel
      revision={0}
      monitors={[]}
      groups={groups}
      onSnapshot={vi.fn()}
    />,
  );
  await screen.findByText("Нет окон обслуживания с выбранными параметрами.");
  fireEvent.click(
    screen.getByRole("button", { name: "+ Добавить обслуживание" }),
  );
  fireEvent.change(screen.getByLabelText("Название обслуживания"), {
    target: { value: "Deploy" },
  });
  fireEvent.change(screen.getByLabelText("Тип объекта обслуживания"), {
    target: { value: "group" },
  });
  fireEvent.change(screen.getByLabelText("Объект обслуживания"), {
    target: { value: "g" },
  });
  fireEvent.change(screen.getByLabelText("Начало"), {
    target: { value: "2026-10-20T12:00:00" },
  });
  fireEvent.change(screen.getByLabelText("Окончание"), {
    target: { value: "2026-10-20T12:30:00" },
  });
  fireEvent.click(screen.getByRole("button", { name: "Создать обслуживание" }));
  await waitFor(() =>
    expect(fetcher.mock.calls.some((c) => c[1]?.method === "POST")).toBe(true),
  );
  const payload = JSON.parse(
    fetcher.mock.calls.find((c) => c[1]?.method === "POST")![1].body,
  );
  expect(payload).toMatchObject({
    name: "Deploy",
    group_id: "g",
    monitor_id: null,
  });
  expect(payload.start_at).toBe(new Date("2026-10-20T12:00:00").toISOString());
  expect(payload.end_at).toBe(new Date("2026-10-20T12:30:00").toISOString());
});

it("validates end before start without calling API", async () => {
  const fetcher = vi
    .fn()
    .mockResolvedValue({ ok: true, json: async () => page });
  vi.stubGlobal("fetch", fetcher);
  render(
    <MaintenancePanel
      revision={0}
      monitors={[]}
      groups={groups}
      onSnapshot={vi.fn()}
    />,
  );
  await screen.findByText("Нет окон обслуживания с выбранными параметрами.");
  fireEvent.click(
    screen.getByRole("button", { name: "+ Добавить обслуживание" }),
  );
  fireEvent.change(screen.getByLabelText("Название обслуживания"), {
    target: { value: "Bad" },
  });
  fireEvent.change(screen.getByLabelText("Начало"), {
    target: { value: "2026-10-20T12:00:00" },
  });
  fireEvent.change(screen.getByLabelText("Окончание"), {
    target: { value: "2026-10-20T11:30:00" },
  });
  fireEvent.submit(
    screen
      .getByRole("button", { name: "Создать обслуживание" })
      .closest("form")!,
  );
  expect(await screen.findByRole("alert")).toHaveProperty(
    "textContent",
    "Окончание должно быть позже начала.",
  );
  expect(fetcher).toHaveBeenCalledTimes(1);
});

it("preserves an edit draft on a version conflict", async () => {
  const window = {
    id: "w",
    name: "Old window",
    group_id: "g",
    monitor_id: null,
    config_version: 1,
    start_at: "2026-10-20T10:00:00Z",
    end_at: "2026-10-20T11:00:00Z",
    state: "UPCOMING",
  };
  vi.stubGlobal(
    "fetch",
    vi.fn().mockImplementation((_url, options) =>
      Promise.resolve(
        options?.method === "PUT"
          ? {
              ok: false,
              status: 409,
              json: async () => ({ detail: "Configuration changed" }),
            }
          : { ok: true, json: async () => ({ ...page, items: [window] }) },
      ),
    ),
  );
  render(
    <MaintenancePanel
      revision={0}
      monitors={[]}
      groups={groups}
      onSnapshot={vi.fn()}
    />,
  );
  await screen.findByText("Old window");
  fireEvent.click(
    screen.getByRole("button", { name: "Изменить обслуживание" }),
  );
  fireEvent.change(screen.getByLabelText("Название обслуживания"), {
    target: { value: "My draft" },
  });
  fireEvent.click(
    screen.getByRole("button", { name: "Сохранить обслуживание" }),
  );
  await screen.findByText(/Ваш черновик сохранён/);
  expect(screen.getByLabelText("Название обслуживания")).toHaveProperty(
    "value",
    "My draft",
  );
  fireEvent.click(
    screen.getByRole("button", {
      name: "Отменить черновик обслуживания и загрузить заново",
    }),
  );
  expect(screen.queryByLabelText("Название обслуживания")).toBeNull();
});
