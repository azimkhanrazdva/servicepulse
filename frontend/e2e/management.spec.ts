import { test, expect } from "@playwright/test";

test("versioned management and groups synchronize across two clients", async ({
  browser,
  request,
}) => {
  const first = await browser.newContext(),
    second = await browser.newContext();
  const a = await first.newPage(),
    b = await second.newPage();
  const name = `Managed ${Date.now()}`,
    finalName = `${name} edited`,
    groupName = `Team ${Date.now()}`;
  const created = await request.post("/api/monitors", {
    data: { name, url: "http://simulator:8090/target/management" },
  });
  const monitor = await created.json();
  let groupId: string | undefined;
  try {
    await Promise.all([a.goto("/"), b.goto("/")]);
    const rowA = () => a.getByRole("row").filter({ hasText: name });
    const rowB = () => b.getByRole("row").filter({ hasText: name });
    await expect(rowA()).toContainText("UP", { timeout: 15000 });
    await rowA().getByRole("button", { name: "Pause", exact: true }).click();
    await expect(rowB()).toContainText("PAUSED");
    await rowA().getByRole("button", { name: "Edit", exact: true }).click();
    await rowB().getByRole("button", { name: "Edit", exact: true }).click();
    await a.getByLabel("Name", { exact: true }).fill(finalName);
    await a.getByLabel("Interval (seconds)").fill("60");
    await a
      .getByLabel("URL", { exact: true })
      .fill("http://simulator:8090/target/management-edited");
    await a.getByRole("button", { name: "Save monitor", exact: true }).click();
    await expect(rowB()).toContainText(finalName);
    await b
      .getByLabel("Name", { exact: true })
      .fill("Unsaved second-client draft");
    await b.getByRole("button", { name: "Save monitor", exact: true }).click();
    await expect(b.getByRole("alert")).toContainText("Configuration changed");
    await expect(b.getByLabel("Name", { exact: true })).toHaveValue(
      "Unsaved second-client draft",
    );
    await b.getByRole("button", { name: "Discard draft and reload" }).click();
    await expect(b.getByLabel("Name", { exact: true })).toHaveValue(finalName);
    await b.getByRole("button", { name: "Cancel", exact: true }).click();

    await a.getByRole("button", { name: "+ Add group" }).click();
    await a.getByLabel("Group name").fill(groupName);
    await a
      .getByLabel("Recipients (one per line)")
      .fill("ops@example.com\nteam@example.com");
    await a.getByRole("checkbox", { name: new RegExp(finalName) }).check();
    const groupCreated = a.waitForResponse(
      (r) => r.url().endsWith("/api/groups") && r.request().method() === "POST",
    );
    await a.getByRole("button", { name: "Create group", exact: true }).click();
    groupId = (await (await groupCreated).json()).id;
    const cardA = () => a.locator(".group-card").filter({ hasText: groupName });
    const cardB = () => b.locator(".group-card").filter({ hasText: groupName });
    await expect(cardB()).toContainText("PAUSED");
    await expect(cardB()).toContainText("2 email recipients");
    await cardA().getByRole("button", { name: "View monitors" }).click();
    await expect(
      a.getByRole("button", { name: `Show all monitors · ${groupName}` }),
    ).toBeVisible();
    await expect(a.locator("#monitors tbody tr")).toHaveCount(1);
    await a
      .getByRole("button", { name: `Show all monitors · ${groupName}` })
      .click();
    await cardA().getByRole("button", { name: "Edit group" }).click();
    await a.getByRole("checkbox", { name: new RegExp(finalName) }).uncheck();
    await a.getByLabel("Recipients (one per line)").fill("");
    await a.getByRole("button", { name: "Save group", exact: true }).click();
    await expect(cardB()).toContainText("UNKNOWN");
    await expect(cardB()).toContainText("0 email recipients");
    a.once("dialog", (d) => d.accept());
    await cardA().getByRole("button", { name: "Delete group" }).click();
    await expect(cardB()).toHaveCount(0);
    groupId = undefined;
    await expect(rowA()).toContainText("PAUSED");
    await rowA().getByRole("button", { name: "Resume", exact: true }).click();
    await expect(rowB()).toContainText("UP", { timeout: 15000 });
    const count = (
      await (await request.get(`/api/monitors/${monitor.id}/results`)).json()
    ).length;
    await expect(
      rowA().getByRole("button", { name: "Run now ↗" }),
    ).toBeEnabled();
    await rowA().getByRole("button", { name: "Run now ↗" }).click();
    await expect
      .poll(
        async () =>
          (
            await (
              await request.get(`/api/monitors/${monitor.id}/results`)
            ).json()
          ).length,
      )
      .toBeGreaterThan(count);
    const saved = await (
      await request.get(`/api/monitors/${monitor.id}`)
    ).json();
    expect(saved.interval_seconds).toBe(60);
    expect(saved.url).toContain("management-edited");
    await a.screenshot({
      path: "../output/playwright/phase2-desktop.png",
      fullPage: true,
    });
    a.once("dialog", (d) => d.dismiss());
    await rowA().getByRole("button", { name: "Delete", exact: true }).click();
    await expect(rowA()).toHaveCount(1);
    a.once("dialog", (d) => d.accept());
    await rowA().getByRole("button", { name: "Delete", exact: true }).click();
    await expect(rowB()).toHaveCount(0);
  } finally {
    if (groupId) {
      const g = await (await request.get(`/api/groups/${groupId}`)).json();
      await request.delete(
        `/api/groups/${groupId}?config_version=${g.config_version}`,
      );
    }
    await request.delete(`/api/monitors/${monitor.id}`);
    await first.close();
    await second.close();
  }
});
