import { test, expect } from "@playwright/test";
import { execFileSync } from "node:child_process";

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

test("confirmed incident opens and recovers in two clients, duration and reconnect", async ({
  browser,
  request,
}) => {
  const contexts = await Promise.all([
    browser.newContext(),
    browser.newContext(),
  ]);
  const [a, b] = await Promise.all(contexts.map((c) => c.newPage()));
  const name = `incident-${Date.now()}`;
  let mid: string | undefined;
  try {
    control(name, 200);
    const response = await request.post("/api/monitors", {
      data: { name, url: `http://simulator:8090/target/${name}` },
    });
    expect(response.status()).toBe(201);
    mid = (await response.json()).id;
    const root = `/api/monitors/${mid}`;
    await expect
      .poll(async () => (await (await request.get(root)).json()).state)
      .toBe("UP");
    await Promise.all([a.goto("/"), b.goto("/")]);
    control(name, 500);
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
    await run();
    expect((await (await request.get(root)).json()).state).toBe("UP");
    expect(
      (await (await request.get(root + "/incidents")).json()).items,
    ).toHaveLength(0);
    await run();
    const incident = (await (await request.get(root + "/incidents")).json())
      .items[0];
    for (const page of [a, b])
      await expect(page.getByTestId(`incident-${incident.id}`)).toContainText(
        "OPEN",
      );
    const duration = a
      .getByTestId(`incident-${incident.id}`)
      .getByTestId("incident-duration");
    const firstDuration = await duration.innerText();
    await expect.poll(() => duration.innerText()).not.toBe(firstDuration);
    await run();
    expect(
      (await (await request.get(root + "/incidents")).json()).items,
    ).toHaveLength(1);
    await contexts[1].setOffline(true);
    await expect(b.getByRole("status")).toContainText("Reconnecting");
    control(name, 200);
    await run();
    await expect(a.getByTestId(`incident-${incident.id}`)).toContainText(
      "RECOVERED",
    );
    await contexts[1].setOffline(false);
    await expect(b.getByTestId(`incident-${incident.id}`)).toContainText(
      "RECOVERED",
    );
    for (const page of [a, b])
      await expect(page.getByTestId(`incident-${incident.id}`)).toContainText(
        "CLOSED",
      );
    await a.screenshot({
      path: "../output/playwright/phase3-incidents.png",
      fullPage: true,
    });
  } finally {
    if (mid) await request.delete(`/api/monitors/${mid}`);
    await Promise.all(contexts.map((c) => c.close()));
  }
});
