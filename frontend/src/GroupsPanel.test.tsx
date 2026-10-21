import { cleanup, fireEvent, render, screen } from "@testing-library/react";
import { afterEach, expect, it, vi } from "vitest";
import { GroupsPanel } from "./GroupsPanel";

afterEach(() => {
  cleanup();
  vi.unstubAllGlobals();
});

it("creates a group and saves recipients, without implying email delivery", async () => {
  const changed = vi.fn(),
    notify = vi.fn();
  const fetcher = vi.fn().mockResolvedValue({
    ok: true,
    json: async () => ({
      id: "g",
      name: "Ops",
      monitor_ids: [],
      recipients: ["ops@example.com"],
      config_version: 1,
      state: "UNKNOWN",
    }),
  });
  vi.stubGlobal("fetch", fetcher);
  render(
    <GroupsPanel
      groups={[]}
      monitors={[]}
      onChange={changed}
      onFilter={() => {}}
      notify={notify}
    />,
  );
  fireEvent.click(screen.getByRole("button", { name: "+ Добавить группу" }));
  fireEvent.change(screen.getByLabelText("Название группы"), {
    target: { value: "Ops" },
  });
  fireEvent.change(screen.getByLabelText("Получатели (по одному в строке)"), {
    target: { value: "ops@example.com\nteam@example.com" },
  });
  expect(
    screen.getByText(
      /Локальная почта поступает в Mailpit\. Обслуживание подавляет соответствующие маршруты\./,
    ),
  ).toBeTruthy();
  fireEvent.click(screen.getByRole("button", { name: "Создать группу" }));
  await screen.findByText(
    "Групп пока нет. Объединяйте мониторы без изменения параметров проверок.",
  );
  expect(JSON.parse(fetcher.mock.calls[0][1].body)).toEqual({
    name: "Ops",
    monitor_ids: [],
    recipients: ["ops@example.com", "team@example.com"],
  });
  expect(changed).toHaveBeenCalled();
});

it("requires confirmation before deleting a group", () => {
  const fetcher = vi.fn();
  vi.stubGlobal("fetch", fetcher);
  vi.stubGlobal("confirm", vi.fn().mockReturnValue(false));
  render(
    <GroupsPanel
      groups={[
        {
          id: "g",
          name: "Ops",
          monitor_ids: [],
          recipients: [],
          state: "UNKNOWN",
          config_version: 1,
        },
      ]}
      monitors={[]}
      onChange={() => {}}
      onFilter={() => {}}
      notify={() => {}}
    />,
  );
  fireEvent.click(screen.getByRole("button", { name: "Удалить группу" }));
  expect(window.confirm).toHaveBeenCalled();
  expect(fetcher).not.toHaveBeenCalled();
});
