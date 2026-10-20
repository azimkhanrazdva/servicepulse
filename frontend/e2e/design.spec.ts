import AxeBuilder from "@axe-core/playwright";
import { test, expect } from "@playwright/test";
import { mkdirSync, writeFileSync } from "node:fs";

for (const [width, height] of [
  [390, 844],
  [768, 1024],
  [1440, 900],
  [1920, 1080],
]) {
  test(`monochrome screens, keyboard and accessibility at ${width}`, async ({
    page,
    request,
  }) => {
    test.setTimeout(90000);
    await page.setViewportSize({ width, height });
    const slug = `visual-${width}-${Date.now()}`;
    const response = await request.post("/api/monitors", {
      data: {
        name: slug,
        url: "http://simulator:8090/target/visual",
        interval_seconds: 3600,
      },
    });
    expect(response.status()).toBe(201);
    const monitor = await response.json();
    let pid: string | undefined;
    const dir = "../output/playwright/phase6-monochrome";
    mkdirSync(dir, { recursive: true });
    const evidence: unknown[] = [];
    try {
      await expect
        .poll(
          async () =>
            (await (await request.get(`/api/monitors/${monitor.id}`)).json())
              .state,
        )
        .toBe("UP");
      await page.goto("/");
      await expect(
        page.getByRole("button", { name: slug, exact: true }),
      ).toBeVisible();
      for (const section of [
        "overview",
        "monitors",
        "groups",
        "incidents",
        "maintenance",
        "notifications",
        "publication",
      ]) {
        await page.goto(`/#${section}`);
        await expect(page.locator(`nav a[href='#${section}']`)).toHaveAttribute(
          "aria-current",
          "page",
        );
        await expect
          .poll(() =>
            page.evaluate(
              () => document.documentElement.scrollWidth <= innerWidth,
            ),
          )
          .toBe(true);
        if (section === "notifications")
          await expect(page.getByText("Loading delivery status…")).toHaveCount(
            0,
          );
        await page.screenshot({ path: `${dir}/${width}-${section}.png` });
      }
      await page.goto("/#monitors");
      await page.getByRole("button", { name: slug, exact: true }).click();
      await expect(page.locator(".uptime-grid")).toBeVisible();
      await page.locator(".detail").scrollIntoViewIfNeeded();
      await expect(page.getByText("Loading availability history…")).toHaveCount(
        0,
      );
      await page.screenshot({ path: `${dir}/${width}-details.png` });
      let result = await new AxeBuilder({ page })
        .withTags(["wcag2a", "wcag2aa", "wcag21aa"])
        .analyze();
      evidence.push({
        surface: "admin-detail",
        violations: result.violations,
        incomplete: result.incomplete.map((x) => x.id),
      });
      expect(result.violations).toEqual([]);
      await page.goto("/#overview");
      if (width <= 650) {
        const toggle = page.getByRole("button", { name: /Workspace menu/ });
        await toggle.focus();
        await page.keyboard.press("Enter");
        await expect(toggle).toHaveAttribute("aria-expanded", "true");
        await page.keyboard.press("Escape");
        await expect(toggle).toHaveAttribute("aria-expanded", "false");
        await expect(toggle).toBeFocused();
      }
      const add = page.getByRole("button", {
        name: "+ Add monitor",
        exact: true,
      });
      await add.focus();
      await page.keyboard.press("Enter");
      const dialog = page.getByRole("dialog");
      await expect(dialog).toBeVisible();
      for (let i = 0; i < 14; i++) {
        await page.keyboard.press("Tab");
        expect(
          await dialog.evaluate((d) => d.contains(document.activeElement)),
        ).toBe(true);
      }
      await page.screenshot({ path: `${dir}/${width}-editor.png` });
      result = await new AxeBuilder({ page })
        .withTags(["wcag2a", "wcag2aa", "wcag21aa"])
        .analyze();
      evidence.push({ surface: "editor", violations: result.violations });
      expect(result.violations).toEqual([]);
      await page.keyboard.press("Escape");
      await expect(dialog).toHaveCount(0);
      await expect(add).toBeFocused();
      const publication = await request.post("/api/status-pages", {
        data: {
          slug,
          title: "Service availability",
          enabled: true,
          publications: [
            {
              monitor_id: monitor.id,
              public_name: "Customer API",
              show_history: true,
            },
          ],
        },
      });
      expect(publication.status()).toBe(201);
      pid = (await publication.json()).id;
      await page
        .context()
        .grantPermissions(["clipboard-read", "clipboard-write"]);
      await page.goto(`/?publication-refresh=${slug}#publication`);
      const card = page
        .locator(".group-card")
        .filter({ has: page.locator(`a[href$="/status/${slug}"]`) });
      await card.getByRole("button", { name: "Copy public link" }).click();
      await expect
        .poll(() => page.evaluate(() => navigator.clipboard.readText()))
        .toBe(`http://127.0.0.1:8081/status/${slug}`);
      await expect(
        card.getByRole("link", { name: "Open public page" }),
      ).toHaveAttribute("href", `http://127.0.0.1:8081/status/${slug}`);
      await page.goto(`http://127.0.0.1:8081/status/${slug}`);
      await expect(page.locator(".uptime-grid")).toBeVisible();
      await expect
        .poll(() =>
          page.evaluate(
            () => document.documentElement.scrollWidth <= innerWidth,
          ),
        )
        .toBe(true);
      await page.screenshot({ path: `${dir}/${width}-public.png` });
      result = await new AxeBuilder({ page })
        .withTags(["wcag2a", "wcag2aa", "wcag21aa"])
        .analyze();
      evidence.push({
        surface: "public",
        violations: result.violations,
        incomplete: result.incomplete.map((x) => x.id),
      });
      expect(result.violations).toEqual([]);
    } finally {
      writeFileSync(
        `../artifacts/phase6-accessibility-${width}.json`,
        JSON.stringify(evidence, null, 2),
      );
      if (pid)
        await request.delete(`/api/status-pages/${pid}?config_version=1`);
      await request.delete(`/api/monitors/${monitor.id}`);
    }
  });
}
