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
  fireEvent.click(screen.getByRole("button", { name: "+ Add group" }));
  fireEvent.change(screen.getByLabelText("Group name"), {
    target: { value: "Ops" },
  });
  fireEvent.change(screen.getByLabelText("Recipients (one per line)"), {
    target: { value: "ops@example.com\nteam@example.com" },
  });
  expect(
    screen.getByText(
      "Recipients are stored. Email delivery is planned for phase 4.",
    ),
  ).toBeTruthy();
  fireEvent.click(screen.getByRole("button", { name: "Create group" }));
  await screen.findByText(
    "No groups yet. Organize monitors without changing their check settings.",
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
  fireEvent.click(screen.getByRole("button", { name: "Delete group" }));
  expect(window.confirm).toHaveBeenCalled();
  expect(fetcher).not.toHaveBeenCalled();
});
