import { test, expect } from "@playwright/test";

test("real form, worker result, two independent clients and SSE reconnect", async ({
  browser,
  request,
}) => {
  const first = await browser.newContext();
  const second = await browser.newContext();
  const a = await first.newPage();
  const b = await second.newPage();
  const name = `Browser ${Date.now()}`;
  const ids: string[] = [];
  try {
    await Promise.all([a.goto("/"), b.goto("/")]);
    await a
      .getByRole("button", { name: "+ Добавить монитор", exact: true })
      .click();
    await a.getByLabel("Название", { exact: true }).fill(name);
    await a
      .getByLabel("URL", { exact: true })
      .fill("http://simulator:8090/target/browser");
    const created = a.waitForResponse(
      (r) =>
        r.url().endsWith("/api/monitors") && r.request().method() === "POST",
    );
    await a
      .getByRole("button", { name: "Создать монитор", exact: true })
      .click();
    const monitor = await (await created).json();
    ids.push(monitor.id);
    const rowA = a.getByRole("row").filter({ hasText: name });
    const rowB = b.getByRole("row").filter({ hasText: name });
    await expect(rowA).toContainText("UP", { timeout: 15000 });
    await expect(rowB).toContainText("UP", { timeout: 15000 });
    await a.getByRole("button", { name, exact: true }).click();
    await expect(
      a.getByRole("heading", { name: "Последние наблюдения" }),
    ).toBeVisible();
    await expect(
      a.getByRole("cell", { name: "Успешно", exact: true }).first(),
    ).toBeVisible();
    await a.screenshot({
      path: "../output/playwright/desktop.png",
      fullPage: true,
    });
    await second.setOffline(true);
    await expect(b.getByRole("status")).toHaveText("● Переподключение");
    const response = await request.post("/api/monitors", {
      data: {
        name: `${name} reconnect`,
        url: "http://simulator:8090/target/reconnect",
      },
    });
    const next = await response.json();
    ids.push(next.id);
    await expect(
      a.getByRole("button", { name: `${name} reconnect`, exact: true }),
    ).toBeVisible();
    await second.setOffline(false);
    await expect(
      b.getByRole("button", { name: `${name} reconnect`, exact: true }),
    ).toBeVisible({ timeout: 15000 });
    await expect(b.getByRole("status")).toHaveText("● На связи");
  } finally {
    for (const id of ids) await request.delete(`/api/monitors/${id}`);
    await first.close();
    await second.close();
  }
});

test("mobile viewport keeps page and create form within screen", async ({
  browser,
}) => {
  const context = await browser.newContext({
    viewport: { width: 390, height: 844 },
  });
  const page = await context.newPage();
  try {
    await page.goto("/");
    await page
      .getByRole("button", { name: "+ Добавить монитор", exact: true })
      .click();
    await expect(
      page.getByRole("heading", { name: "Новый монитор" }),
    ).toBeVisible();
    expect(
      await page.evaluate(
        () => document.documentElement.scrollWidth <= window.innerWidth,
      ),
    ).toBe(true);
    await page.screenshot({
      path: "../output/playwright/mobile.png",
      fullPage: true,
    });
  } finally {
    await context.close();
  }
});
