import { chromium } from "@playwright/test";
import { writeFile, access } from "node:fs/promises";
const browser = await chromium.launch();
const contexts = await Promise.all([
  browser.newContext(),
  browser.newContext(),
]);
const pages = [];
const report = { started_at: new Date().toISOString(), clients: [] };
try {
  for (const context of contexts) {
    await context.addInitScript(() => {
      window.faultEvidence = { snapshots: 0, states: [], incidents: [] };
      const Native = window.EventSource;
      window.EventSource = class extends Native {
        constructor(url) {
          super(url);
          this.addEventListener("message", (event) => {
            const rows = JSON.parse(event.data);
            window.faultEvidence.snapshots++;
            const row = rows.find((r) => r.name === "fault-00");
            if (row) window.faultEvidence.states.push(row.state);
          });
          this.addEventListener("incidents", (event) => {
            for (const incident of JSON.parse(event.data).items) {
              if (incident.monitor_name === "fault-00")
                window.faultEvidence.incidents.push(incident.state);
            }
          });
        }
      };
    });
    const page = await context.newPage();
    await page.goto("http://127.0.0.1:19080");
    await page.getByRole("button", { name: "fault-49", exact: true }).waitFor();
    await page.waitForFunction(() => window.faultEvidence.snapshots > 0);
    pages.push(page);
  }
  await writeFile("../artifacts/local/fault-browser-ready", "ready");
  const start = Date.now();
  let reconnected = false;
  while (Date.now() - start < 240000) {
    if (!reconnected && Date.now() - start > 20000) {
      const before = await pages[1].evaluate(
        () => window.faultEvidence.snapshots,
      );
      await contexts[1].setOffline(true);
      await new Promise((r) => setTimeout(r, 1200));
      await contexts[1].setOffline(false);
      await pages[1].waitForFunction(
        (n) => window.faultEvidence.snapshots > n,
        before,
      );
      await pages[1].getByText("Live", { exact: false }).first().waitFor();
      reconnected = true;
    }
    try {
      await access("../artifacts/local/fault-browser-stop");
      break;
    } catch {
      /* running */
    }
    await new Promise((r) => setTimeout(r, 500));
  }
  for (const page of pages) {
    const evidence = await page.evaluate(() => window.faultEvidence);
    if (
      !evidence.states.includes("DOWN") ||
      !evidence.states.includes("UP") ||
      !evidence.incidents.includes("OPEN") ||
      !evidence.incidents.includes("CLOSED")
    )
      throw new Error("Client missed actual DOWN/UP/incidents");
    report.clients.push(evidence);
  }
  report.reconnected = reconnected;
  report.status = "PASS";
} catch (error) {
  report.status = "FAIL";
  report.error = String(error);
  process.exitCode = 1;
} finally {
  await writeFile(
    "../artifacts/phase6-fault-browser.json",
    JSON.stringify(report, null, 2),
  );
  await browser.close();
}
