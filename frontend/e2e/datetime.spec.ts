import { test, expect } from "@playwright/test";
import { localDateTime } from "./datetime";

test("datetime-local fill preserves zero and nonzero seconds without clock-dependent failures", async ({
  page,
}) => {
  await page.setContent('<input type="datetime-local" step="1" required>');
  const input = page.locator("input");
  for (const [hour, minute, second, expected] of [
    [7, 35, 0, "2026-10-21T07:35"],
    [7, 35, 1, "2026-10-21T07:35:01"],
    [23, 59, 59, "2026-10-21T23:59:59"],
    [0, 0, 0, "2026-10-21T00:00"],
  ] as const) {
    const value = localDateTime(
      new Date(2026, 9, 21, hour, minute, second).getTime(),
    );
    expect(value).toBe(expected);
    await input.fill(value);
    await expect(input).toHaveValue(expected);
    expect(
      await input.evaluate((element: HTMLInputElement) =>
        element.checkValidity(),
      ),
    ).toBe(true);
  }
});
