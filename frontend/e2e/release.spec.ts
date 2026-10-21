import { test, expect } from "@playwright/test";
import { execFileSync } from "node:child_process";
import { writeFileSync } from "node:fs";

test("complete release journey with real HTTP, maintenance, Mailpit and public revocation", async ({
  browser,
  request,
}) => {
  test.setTimeout(120000);
  const name = `release-${Date.now()}`,
    email = `${name}@example.com`;
  const publicBase = process.env.PUBLIC_BASE_URL ?? "http://127.0.0.1:8081";
  const mailBase = process.env.MAILPIT_BASE_URL ?? "http://127.0.0.1:8025";
  const composeArgs: string[] = JSON.parse(
    process.env.SERVICEPULSE_COMPOSE_ARGS ?? "[]",
  );
  const contexts = await Promise.all([
    browser.newContext(),
    browser.newContext(),
    browser.newContext(),
    browser.newContext(),
  ]);
  const [a, b, c, d] = await Promise.all(
    contexts.map((context) => context.newPage()),
  );
  let mid: string | undefined,
    gid: string | undefined,
    wid: string | undefined,
    pid: string | undefined;
  const evidence: Record<string, unknown> = {
    started_at: new Date().toISOString(),
    name,
  };
  function control(status: number, redirect: string | null = null) {
    execFileSync(
      "docker",
      [
        "compose",
        ...composeArgs,
        "exec",
        "-T",
        "backend",
        "python",
        "-c",
        "import sys,urllib.request; urllib.request.urlopen(urllib.request.Request('http://simulator:8090/control/'+sys.argv[1],data=sys.argv[2].encode(),headers={'Content-Type':'application/json'},method='PUT')).close()",
        name,
        JSON.stringify({ status, body: "Release ready", redirect }),
      ],
      { cwd: ".." },
    );
  }
  async function messages() {
    const response = await request.get(`${mailBase}/api/v1/messages?limit=100`);
    expect(response.status()).toBe(200);
    return (await response.json()).messages.filter(
      (m: { To: { Address: string }[] }) =>
        m.To.some((to) => to.Address === email),
    );
  }
  async function run() {
    const before = await (
      await request.get(`/api/monitors/${mid}/results`)
    ).json();
    expect((await request.post(`/api/monitors/${mid}/run`)).status()).toBe(202);
    await expect
      .poll(
        async () =>
          (await (await request.get(`/api/monitors/${mid}/results`)).json())[0]
            ?.id,
        { timeout: 15000 },
      )
      .not.toBe(before[0]?.id);
  }
  function local(ms: number) {
    const date = new Date(ms);
    return new Date(ms - date.getTimezoneOffset() * 60000)
      .toISOString()
      .slice(0, 19);
  }
  try {
    control(200);
    await Promise.all([a.goto("/"), b.goto("/")]);
    await expect(a.locator("html")).toHaveAttribute("lang", "ru");
    await a
      .getByRole("button", { name: "+ Добавить монитор", exact: true })
      .click();
    await a
      .getByRole("button", { name: "Создать монитор", exact: true })
      .click();
    await expect
      .poll(() =>
        a
          .getByLabel("Название", { exact: true })
          .evaluate((input: HTMLInputElement) => input.validationMessage),
      )
      .toBe("Заполните это поле.");
    await a.getByLabel("Название", { exact: true }).fill(name);
    await a
      .getByLabel("URL", { exact: true })
      .fill(`http://simulator:8090/target/${name}`);
    await a.getByLabel("Интервал (секунды)").fill("30");
    await a.getByLabel("Ожидаемый текст (необязательно)").fill("Release ready");
    const created = a.waitForResponse(
      (r) =>
        r.url().endsWith("/api/monitors") && r.request().method() === "POST",
    );
    await a
      .getByRole("button", { name: "Создать монитор", exact: true })
      .click();
    const monitor = await (await created).json();
    mid = monitor.id;
    const row = (page: typeof a) =>
      page.locator("#monitors tbody tr").filter({ hasText: name });
    await expect(row(a)).toContainText("UP", { timeout: 15000 });
    await expect(row(b)).toContainText("UP");
    await expect(row(a)).toContainText("200");
    await a.getByRole("button", { name, exact: true }).click();
    await expect(a.locator(".detail .uptime-grid")).toBeVisible();
    await row(a).getByRole("button", { name: "Изменить", exact: true }).click();
    await a.getByLabel("Интервал (секунды)").fill("3600");
    await a
      .getByRole("button", { name: "Сохранить монитор", exact: true })
      .click();
    await expect(row(b)).toContainText("UP");
    await a.getByRole("button", { name: "+ Добавить группу" }).click();
    await a.getByLabel("Название группы").fill(name);
    await a.getByLabel("Получатели (по одному в строке)").fill(email);
    await a.getByRole("checkbox", { name: new RegExp(name) }).check();
    const grouped = a.waitForResponse(
      (r) => r.url().endsWith("/api/groups") && r.request().method() === "POST",
    );
    await a
      .getByRole("button", { name: "Создать группу", exact: true })
      .click();
    gid = (await (await grouped).json()).id;
    await expect(b.locator("#groups")).toContainText(email);
    await a.getByRole("button", { name: "+ Добавить обслуживание" }).click();
    await a.getByLabel("Название обслуживания", { exact: true }).fill(name);
    await a.getByLabel("Тип объекта обслуживания").selectOption("monitor");
    await a
      .getByRole("combobox", { name: "Объект обслуживания", exact: true })
      .selectOption(mid!);
    await a.getByLabel("Начало").fill(local(Date.now() - 1000));
    await a.getByLabel("Окончание").fill(local(Date.now() + 300000));
    const maintained = a.waitForResponse(
      (r) =>
        r.url().endsWith("/api/maintenance") && r.request().method() === "POST",
    );
    await a
      .getByRole("button", { name: "Создать обслуживание", exact: true })
      .click();
    wid = (await (await maintained).json()).id;
    control(500);
    await run();
    await run();
    await expect(row(b)).toContainText("DOWN");
    await expect(row(b)).toContainText("ОБСЛУЖИВАНИЕ");
    expect(await messages()).toHaveLength(0);
    control(200);
    await run();
    await expect(row(b)).toContainText("UP");
    a.once("dialog", (dialog) => dialog.accept());
    await a
      .getByTestId(`window-${wid}`)
      .getByRole("button", { name: "Удалить обслуживание" })
      .click();
    await expect(a.getByTestId(`window-${wid}`)).toHaveCount(0);
    wid = undefined;
    control(500);
    await run();
    expect(
      (await (await request.get(`/api/monitors/${mid}`)).json()).state,
    ).toBe("UP");
    await run();
    await expect(row(b)).toContainText("DOWN");
    await expect
      .poll(async () => (await messages()).length, { timeout: 15000 })
      .toBe(1);
    await run();
    expect(await messages()).toHaveLength(1);
    control(200);
    await run();
    await expect(row(b)).toContainText("UP");
    await expect
      .poll(async () => (await messages()).length, { timeout: 15000 })
      .toBe(2);
    const accepted = await messages();
    expect(
      accepted.some((m: { Subject: string }) => m.Subject.includes("DOWN:")),
    ).toBe(true);
    expect(
      accepted.some((m: { Subject: string }) =>
        m.Subject.includes("RECOVERY:"),
      ),
    ).toBe(true);
    evidence.messages = accepted.map((m: { ID: string; Subject: string }) => ({
      id: m.ID,
      subject: m.Subject,
    }));
    await a.getByRole("button", { name: "+ Создать страницу" }).click();
    await a.getByLabel("Заголовок публичной страницы").fill(name);
    await a.getByLabel("Адрес страницы (slug)").fill(name);
    await a.getByLabel("Разрешить публичный доступ к странице").check();
    await a.getByLabel(`Опубликовать ${name}`, { exact: true }).check();
    await a
      .getByLabel(`Публичное название для ${name}`, { exact: true })
      .fill("Опубликованный сервис");
    await a
      .getByLabel(`Опубликовать агрегированную историю для ${name}`, {
        exact: true,
      })
      .check();
    const published = a.waitForResponse(
      (r) =>
        r.url().endsWith("/api/status-pages") &&
        r.request().method() === "POST",
    );
    await a
      .getByRole("button", { name: "Сохранить публикацию", exact: true })
      .click();
    pid = (await (await published).json()).id;
    await Promise.all([
      c.goto(`${publicBase}/status/${name}`),
      d.goto(`${publicBase}/status/${name}`),
    ]);
    for (const page of [c, d]) {
      await expect(
        page.getByRole("heading", { name: "Опубликованный сервис" }),
      ).toBeVisible();
      await expect(page.locator(".uptime-grid")).toBeVisible();
      expect(await page.locator("body").textContent()).not.toContain(email);
    }
    await row(a)
      .getByRole("button", { name: "Приостановить", exact: true })
      .click();
    for (const page of [c, d])
      await expect(page.locator(".public-service .status")).toContainText(
        "PAUSED",
      );
    await row(a)
      .getByRole("button", { name: "Возобновить", exact: true })
      .click();
    for (const page of [c, d])
      await expect(page.locator(".public-service .status")).toContainText(
        "UP",
        { timeout: 15000 },
      );
    const card = a
      .locator(".publication-pages .group-card")
      .filter({ has: a.locator(`a[href$='/status/${name}']`) });
    await card.getByRole("button", { name: "Изменить публикацию" }).click();
    await a.getByLabel(`Опубликовать ${name}`, { exact: true }).uncheck();
    await a
      .getByRole("button", { name: "Сохранить публикацию", exact: true })
      .click();
    for (const page of [c, d])
      await expect(
        page.getByRole("heading", { name: "Опубликованный сервис" }),
      ).toHaveCount(0);
    // Actual redirect response must be recorded; following it would return200 and fail this assertion.
    control(200, `http://simulator:8090/target/${name}-destination`);
    await run();
    const last = (
      await (await request.get(`/api/monitors/${mid}/results`)).json()
    )[0];
    expect(last.status_code).toBe(302);
    expect(last.success).toBe(false);
    expect(last.error).toBe("unexpected_status");
    evidence.redirect = { status: last.status_code, error: last.error };
    evidence.status = "PASS";
  } catch (error) {
    evidence.status = "FAIL";
    evidence.error = String(error);
    throw error;
  } finally {
    evidence.ended_at = new Date().toISOString();
    writeFileSync(
      process.env.RELEASE_EVIDENCE_PATH ??
        "../artifacts/phase7-release-journey.json",
      JSON.stringify(evidence, null, 2),
    );
    for (const [path, id] of [
      ["status-pages", pid],
      ["maintenance", wid],
      ["groups", gid],
      ["monitors", mid],
    ]) {
      if (!id) continue;
      const response = await request.get(`/api/${path}/${id}`);
      if (response.ok())
        await request.delete(
          `/api/${path}/${id}?config_version=${(await response.json()).config_version}`,
        );
    }
    await Promise.all(contexts.map((context) => context.close()));
  }
});
