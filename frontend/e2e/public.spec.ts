import { test, expect } from "@playwright/test";
import { execFileSync } from "node:child_process";
import { writeFileSync } from "node:fs";

function control(name: string, status: number, delay = 0) {
  execFileSync(
    "docker",
    [
      "compose",
      "exec",
      "-T",
      "backend",
      "python",
      "-c",
      "import sys,json,urllib.request; r=urllib.request.Request('http://simulator:8090/control/'+sys.argv[1],data=json.dumps({'status':int(sys.argv[2]),'delay':float(sys.argv[3])}).encode(),headers={'Content-Type':'application/json'},method='PUT'); urllib.request.urlopen(r).close()",
      name,
      String(status),
      String(delay),
    ],
    { cwd: ".." },
  );
}

test("explicit publication, private REST/SSE isolation, real analytics and two public clients", async ({
  browser,
  request,
  page: admin,
}) => {
  test.setTimeout(90000);
  const marker = `public-${Date.now()}`,
    slug = marker;
  const contexts = await Promise.all([
    browser.newContext(),
    browser.newContext({ viewport: { width: 390, height: 844 } }),
  ]);
  const [a, b] = await Promise.all(contexts.map((c) => c.newPage()));
  let mid: string | undefined,
    hid: string | undefined,
    pid: string | undefined,
    gid: string | undefined;
  try {
    control(marker, 200);
    const created = await request.post("/api/monitors", {
      data: {
        name: `PRIVATE-${marker}`,
        url: `http://simulator:8090/target/${marker}?test-secret=PRIVATE-URL`,
        interval_seconds: 3600,
      },
    });
    expect(created.status()).toBe(201);
    mid = (await created.json()).id;
    const hidden = await request.post("/api/monitors", {
      data: {
        name: `HIDDEN-${marker}`,
        url: `http://simulator:8090/target/${marker}`,
        interval_seconds: 3600,
      },
    });
    hid = (await hidden.json()).id;
    const group = await request.post("/api/groups", {
      data: {
        name: `PRIVATE-GROUP-${marker}`,
        monitor_ids: [mid],
        recipients: [`${marker}@example.com`],
      },
    });
    gid = (await group.json()).id;
    const root = `/api/monitors/${mid}`;
    await expect
      .poll(async () => (await (await request.get(root)).json()).state)
      .toBe("UP");
    await admin.goto("/");
    await admin.getByRole("button", { name: "+ Create status page" }).click();
    await admin.getByLabel("Public page title").fill("Customer service health");
    await admin.getByLabel("Public page slug").fill(slug);
    await admin.getByLabel("Page is publicly enabled").check();
    await admin
      .getByLabel(`Publish PRIVATE-${marker}`, { exact: true })
      .check();
    await admin
      .getByLabel(`Public label for PRIVATE-${marker}`, { exact: true })
      .fill("Customer API");
    await admin
      .getByLabel(`Publish aggregated history for PRIVATE-${marker}`, {
        exact: true,
      })
      .check();
    const save = admin.waitForResponse(
      (r) =>
        r.url().endsWith("/api/status-pages") &&
        r.request().method() === "POST",
    );
    await admin.getByRole("button", { name: "Save publication" }).click();
    const saved = await save;
    expect(saved.status()).toBe(201);
    let config = await saved.json();
    pid = config.id;
    const publicId = config.publications[0].id;
    const base = `http://127.0.0.1:8081/api/public/pages/${slug}`;
    const response = await request.get(base);
    expect(response.status()).toBe(200);
    const safe = await response.json();
    expect(safe.services).toHaveLength(1);
    expect(safe.services[0].id).not.toBe(mid);
    for (const forbidden of [
      mid!,
      hid!,
      `PRIVATE-${marker}`,
      `HIDDEN-${marker}`,
      "PRIVATE-URL",
      gid!,
      `${marker}@example.com`,
      "config_version",
      "expected_body",
      "http://simulator",
    ]) {
      expect(JSON.stringify(safe)).not.toContain(forbidden);
    }
    for (const path of [
      "/api/monitors",
      "/api/overview",
      "/api/events",
      "/api/groups",
      "/api/incidents",
      "/api/notifications",
      "/api/maintenance",
      "/api/status-pages",
      "/openapi.json",
      "/docs",
    ]) {
      expect((await request.get(`http://127.0.0.1:8081${path}`)).status()).toBe(
        404,
      );
      expect(
        (
          await request.post(`http://127.0.0.1:8081${path}`, { data: {} })
        ).status(),
      ).toBe(404);
    }
    await Promise.all([
      a.goto(`http://127.0.0.1:8081/status/${slug}`),
      b.goto(`http://127.0.0.1:8081/status/${slug}`),
    ]);
    const observedSSE = await a.evaluate(
      async (url) =>
        new Promise<string>((resolve, reject) => {
          const events = new EventSource(url);
          const timer = setTimeout(() => {
            events.close();
            reject(new Error("No public SSE"));
          }, 10000);
          events.addEventListener("status", (event) => {
            clearTimeout(timer);
            events.close();
            resolve((event as MessageEvent).data);
          });
        }),
      base + "/events",
    );
    expect(JSON.parse(observedSSE)).toEqual(safe);
    for (const p of [a, b]) {
      await expect(p.getByTestId(`public-${publicId}`)).toContainText("● UP");
      await expect(
        p.getByRole("img", {
          name: "Response time chart with observation gaps",
        }),
      ).toBeVisible();
      await expect(p.getByText("100.00%", { exact: true })).toHaveCount(3);
    }
    expect(
      await b.evaluate(
        () => document.documentElement.scrollWidth <= innerWidth,
      ),
    ).toBe(true);
    await a.getByLabel("History period").selectOption("30d");
    expect(await a.locator("svg [data-gap]").count()).toBeGreaterThan(300);
    const month = await (
      await request.get(`${base}/services/${publicId}/analytics?period=30d`)
    ).json();
    expect(month.buckets).toHaveLength(360);
    expect(month.samples).toBeGreaterThan(0);
    expect(month.coverage_percent).toBeLessThan(1);
    await a.screenshot({
      path: "../output/playwright/phase5-public.png",
      fullPage: true,
    });
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
    control(marker, 500);
    await run();
    await run();
    await expect(
      admin
        .locator("#monitors")
        .getByRole("row")
        .filter({ hasText: `PRIVATE-${marker}` }),
    ).toContainText(/0h 0m \d+s/);
    await expect
      .poll(async () =>
        Number(
          await admin
            .locator(".stats article")
            .filter({ hasText: "Active incidents" })
            .locator("strong")
            .textContent(),
        ),
      )
      .toBeGreaterThan(0);
    for (const p of [a, b])
      await expect(p.getByTestId(`public-${publicId}`)).toContainText("● DOWN");
    await contexts[1].setOffline(true);
    await expect(b.getByRole("status")).toContainText("Reconnecting");
    control(marker, 200);
    await run();
    await expect(a.getByTestId(`public-${publicId}`)).toContainText("● UP");
    await contexts[1].setOffline(false);
    await expect(b.getByTestId(`public-${publicId}`)).toContainText("● UP");
    async function update(changes: object) {
      const result = await request.put(`/api/status-pages/${pid}`, {
        data: {
          slug: config.slug,
          title: config.title,
          enabled: config.enabled,
          config_version: config.config_version,
          publications: config.publications.map(
            (p: {
              monitor_id: string;
              public_name: string;
              show_history: boolean;
            }) => ({
              monitor_id: p.monitor_id,
              public_name: p.public_name,
              show_history: p.show_history,
            }),
          ),
          ...changes,
        },
      });
      expect(result.status()).toBe(200);
      config = await result.json();
    }
    await update({
      publications: [
        { monitor_id: mid, public_name: "Customer API", show_history: false },
      ],
    });
    for (const p of [a, b]) await expect(p.getByRole("img")).toHaveCount(0);
    expect(
      (await request.get(`${base}/services/${publicId}/analytics`)).status(),
    ).toBe(404);
    await update({ publications: [] });
    for (const p of [a, b])
      await expect(p.getByText("No services published")).toBeVisible();
    await update({ enabled: false });
    for (const p of [a, b]) {
      await expect(p.getByRole("alert")).toContainText("unavailable");
      await expect(p.getByText("Customer API", { exact: true })).toHaveCount(0);
    }
    expect((await (await request.get(root)).json()).config_version).toBe(1);
    writeFileSync(
      "../artifacts/phase5-public-browser.json",
      JSON.stringify(
        {
          recorded_at: new Date().toISOString(),
          status: "PASS",
          public_rest: safe,
          public_sse: JSON.parse(observedSSE),
          month_bucket_count: month.buckets.length,
          month_samples: month.samples,
          month_coverage_percent: month.coverage_percent,
          checks: [
            "admin_opt_in",
            "route_isolation",
            "explicit_projection",
            "history_permission",
            "two_public_clients",
            "reconnect",
            "live_DOWN_UP",
            "revocation",
            "NO_DATA_gaps",
            "mobile",
          ],
        },
        null,
        2,
      ),
    );
  } finally {
    if (pid) {
      const pages = await (await request.get("/api/status-pages")).json();
      const current = pages.find((p: { id: string }) => p.id === pid);
      if (current)
        await request.delete(
          `/api/status-pages/${pid}?config_version=${current.config_version}`,
        );
    }
    if (gid) await request.delete(`/api/groups/${gid}?config_version=1`);
    if (mid) await request.delete(`/api/monitors/${mid}`);
    if (hid) await request.delete(`/api/monitors/${hid}`);
    await Promise.allSettled(contexts.map((c) => c.close()));
  }
});

test("a published paused service with no observations renders NO DATA, not healthy history", async ({
  request,
  page,
}) => {
  const name = `no-data-${Date.now()}`;
  let mid: string | undefined, pid: string | undefined;
  try {
    control(name, 200, 30);
    const response = await request.post("/api/monitors", {
      data: {
        name: `PRIVATE-${name}`,
        url: `http://simulator:8090/target/${name}`,
        interval_seconds: 3600,
        timeout_seconds: 60,
      },
    });
    expect(response.status()).toBe(201);
    const m = await response.json();
    mid = m.id;
    expect(
      (
        await request.post(`/api/monitors/${mid}/pause`, {
          data: { config_version: 1 },
        })
      ).status(),
    ).toBe(200);
    expect(
      await (await request.get(`/api/monitors/${mid}/results`)).json(),
    ).toEqual([]);
    const created = await request.post("/api/status-pages", {
      data: {
        slug: name,
        title: "Awaiting observations",
        enabled: true,
        publications: [
          {
            monitor_id: mid,
            public_name: "Unobserved service",
            show_history: true,
          },
        ],
      },
    });
    expect(created.status()).toBe(201);
    pid = (await created.json()).id;
    await page.goto(`http://127.0.0.1:8081/status/${name}`);
    await expect(page.locator(".uptime-grid strong")).toHaveText([
      "NO DATA",
      "NO DATA",
      "NO DATA",
    ]);
    await expect(page.getByText("100.00%", { exact: true })).toHaveCount(0);
    await page.getByLabel("History period").selectOption("30d");
    await expect(page.locator("svg [data-gap]")).toHaveCount(360);
    expect(
      (await (await request.get(`/api/monitors/${mid}`)).json()).state,
    ).toBe("PAUSED");
  } finally {
    if (pid) await request.delete(`/api/status-pages/${pid}?config_version=1`);
    if (mid) await request.delete(`/api/monitors/${mid}`);
  }
});
