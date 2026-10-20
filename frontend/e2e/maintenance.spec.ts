import { test, expect } from "@playwright/test";
import { execFileSync } from "node:child_process";
import { writeFileSync } from "node:fs";

function control(name: string, status: number) {
  execFileSync(
    "docker",
    [
      "compose",
      "exec",
      "-T",
      "backend",
      "python",
      "-c",
      "import sys,urllib.request; r=urllib.request.Request('http://simulator:8090/control/'+sys.argv[1],data=('{\"status\":'+sys.argv[2]+'}').encode(),headers={'Content-Type':'application/json'},method='PUT'); urllib.request.urlopen(r).close()",
      name,
      String(status),
    ],
    { cwd: ".." },
  );
}
function local(value: number) {
  const d = new Date(value);
  return new Date(value - d.getTimezoneOffset() * 60000)
    .toISOString()
    .slice(0, 19);
}

test("maintenance CRUD, two clients, DOWN state, suppression and actual Mailpit release", async ({
  browser,
  request,
}) => {
  test.setTimeout(90000);
  const contexts = await Promise.all([
    browser.newContext(),
    browser.newContext(),
  ]);
  const [a, b] = await Promise.all(contexts.map((c) => c.newPage()));
  const name = `maintenance-${Date.now()}`;
  const email = name + "@example.com";
  let mid: string | undefined, gid: string | undefined, wid: string | undefined;
  async function messages() {
    const response = await request.get(
      "http://127.0.0.1:8025/api/v1/messages?limit=100",
    );
    const data = await response.json();
    return data.messages.filter((m: { To: { Address: string }[] }) =>
      m.To.some((t) => t.Address === email),
    );
  }
  try {
    control(name, 200);
    const created = await request.post("/api/monitors", {
      data: {
        name,
        url: `http://simulator:8090/target/${name}`,
        interval_seconds: 3600,
      },
    });
    expect(created.status()).toBe(201);
    mid = (await created.json()).id;
    const root = `/api/monitors/${mid}`;
    await expect
      .poll(async () => (await (await request.get(root)).json()).state)
      .toBe("UP");
    const group = await request.post("/api/groups", {
      data: { name, monitor_ids: [mid], recipients: [email] },
    });
    expect(group.status()).toBe(201);
    gid = (await group.json()).id;
    await Promise.all([a.goto("/"), b.goto("/")]);
    await expect(a.locator("#groups")).toContainText(email);
    await a.getByRole("button", { name: "+ Add maintenance" }).click();
    await a.getByLabel("Maintenance name", { exact: true }).fill(name);
    await a.getByLabel("Maintenance target type").selectOption("group");
    await a
      .getByRole("combobox", { name: "Maintenance target", exact: true })
      .selectOption(gid!);
    await a.getByLabel("Starts at").fill(local(Date.now() - 1000));
    await a.getByLabel("Ends at").fill(local(Date.now() + 60000));
    const saved = a.waitForResponse(
      (r) =>
        r.url().endsWith("/api/maintenance") && r.request().method() === "POST",
    );
    await a
      .getByRole("button", { name: "Create maintenance", exact: true })
      .click();
    const response = await saved;
    expect(response.status()).toBe(201);
    wid = (await response.json()).id;
    for (const page of [a, b]) {
      await expect(page.getByTestId(`window-${wid}`)).toContainText("ACTIVE");
      await expect(
        page.locator("#monitors").getByRole("row").filter({ hasText: name }),
      ).toContainText("MAINTENANCE");
    }
    async function run() {
      const before = (await (await request.get(root + "/results")).json())
        .length;
      expect((await request.post(root + "/run")).status()).toBe(202);
      await expect
        .poll(
          async () =>
            (await (await request.get(root + "/results")).json()).length,
        )
        .toBeGreaterThan(before);
    }
    control(name, 500);
    await run();
    await run();
    await run();
    for (const page of [a, b])
      await expect(
        page.locator("#monitors").getByRole("row").filter({ hasText: name }),
      ).toContainText("● DOWN");
    expect(await messages()).toHaveLength(0);
    await a
      .getByTestId(`window-${wid}`)
      .getByRole("button", { name: "Edit maintenance" })
      .click();
    await a
      .getByLabel("Maintenance name", { exact: true })
      .fill(name + " edited");
    await a.getByLabel("Ends at").fill(local(Date.now() + 4000));
    await a
      .getByRole("button", { name: "Save maintenance", exact: true })
      .click();
    await contexts[1].setOffline(true);
    await expect(b.getByRole("status")).toContainText("Reconnecting");
    await expect(a.getByTestId(`window-${wid}`)).toContainText("ENDED", {
      timeout: 15000,
    });
    await contexts[1].setOffline(false);
    await expect(b.getByTestId(`window-${wid}`)).toContainText("ENDED");
    await expect(b.locator("#maintenance").getByRole("alert")).toHaveCount(0);
    for (const page of [a, b])
      await expect(
        page.locator("#monitors").getByRole("row").filter({ hasText: name }),
      ).not.toContainText("MAINTENANCE");
    await expect
      .poll(async () => (await messages()).length, { timeout: 15000 })
      .toBe(1);
    const before = await messages();
    expect(before[0].Subject).toContain("DOWN");
    control(name, 200);
    await run();
    await expect
      .poll(async () => (await messages()).length, { timeout: 15000 })
      .toBe(2);
    const accepted = await messages();
    expect(
      accepted.some((m: { Subject: string }) => m.Subject.includes("RECOVERY")),
    ).toBe(true);
    await a.screenshot({
      path: "../output/playwright/phase4-maintenance.png",
      fullPage: true,
    });
    a.once("dialog", (dialog) => dialog.accept());
    await a
      .getByTestId(`window-${wid}`)
      .getByRole("button", { name: "Delete maintenance" })
      .click();
    for (const page of [a, b])
      await expect(page.getByTestId(`window-${wid}`)).toHaveCount(0);
    wid = undefined;
    writeFileSync(
      "../artifacts/phase4-browser-mail.json",
      JSON.stringify(
        {
          recorded_at: new Date().toISOString(),
          status: "PASS",
          messages: accepted.map((m: { ID: string; Subject: string }) => ({
            id: m.ID,
            subject: m.Subject,
          })),
        },
        null,
        2,
      ),
    );
  } finally {
    if (wid) {
      const data = await (
        await fetch("http://127.0.0.1:8080/api/maintenance")
      ).json();
      const w = data.items.find((v: { id: string }) => v.id === wid);
      if (w)
        await fetch(
          `http://127.0.0.1:8080/api/maintenance/${wid}?config_version=${w.config_version}`,
          { method: "DELETE" },
        );
    }
    if (gid)
      await fetch(`http://127.0.0.1:8080/api/groups/${gid}?config_version=1`, {
        method: "DELETE",
      });
    if (mid)
      await fetch(`http://127.0.0.1:8080/api/monitors/${mid}`, {
        method: "DELETE",
      });
    await Promise.allSettled(contexts.map((c) => c.close()));
  }
});
