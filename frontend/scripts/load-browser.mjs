import { chromium } from "@playwright/test";
import { mkdir, writeFile } from "node:fs/promises";
import { performance } from "node:perf_hooks";

const browser = await chromium.launch();
const report = {
  started_at: new Date().toISOString(),
  theme: "v0.5 baseline",
  viewports: [],
};
try {
  await mkdir("../output/playwright/phase6-baseline", { recursive: true });
  for (const [width, height] of [
    [390, 844],
    [768, 1024],
    [1440, 900],
    [1920, 1080],
  ]) {
    const page = await browser.newPage({ viewport: { width, height } });
    const start = performance.now();
    await page.goto("http://127.0.0.1:19080");
    await page.getByRole("button", { name: "load-49", exact: true }).waitFor();
    const elapsed = performance.now() - start;
    const overflow = await page.evaluate(
      () => document.documentElement.scrollWidth > innerWidth,
    );
    const overflowing = await page.evaluate(() =>
      [...document.querySelectorAll("main *")]
        .filter((node) => node.getBoundingClientRect().right > innerWidth + 1)
        .slice(0, 12)
        .map((node) => ({
          tag: node.tagName,
          class: node.className,
          right: node.getBoundingClientRect().right,
          text: node.textContent?.slice(0, 60),
        })),
    );
    await page.screenshot({
      path: `../output/playwright/phase6-baseline/${width}.png`,
      fullPage: true,
    });
    report.viewports.push({
      width,
      height,
      all_50_rendered_ms: elapsed,
      document_overflow: overflow,
      overflowing,
    });
    await page.close();
  }
  if (report.viewports.some((item) => item.document_overflow))
    throw new Error("Viewport overflow; see report");
  report.status = "PASS";
} catch (error) {
  report.status = "FAIL";
  report.error = String(error);
  throw error;
} finally {
  report.ended_at = new Date().toISOString();
  await writeFile(
    "../artifacts/phase6-load-browser.json",
    JSON.stringify(report, null, 2),
  );
  await browser.close();
  console.log(JSON.stringify(report, null, 2));
}
