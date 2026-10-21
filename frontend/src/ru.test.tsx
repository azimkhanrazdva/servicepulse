import { afterEach, expect, it, vi } from "vitest";
import { request, ApiError } from "./api";
import { statusLabel, validationError, installRussianValidation } from "./ru";

afterEach(() => {
  vi.unstubAllGlobals();
  document.body.innerHTML = "";
});

it("keeps API error status and hides untranslated internal server details", async () => {
  vi.stubGlobal(
    "fetch",
    vi.fn().mockResolvedValue({
      ok: false,
      status: 500,
      json: async () => ({ detail: "INTERNAL SENTINEL" }),
    }),
  );
  try {
    await request("/ready");
    throw new Error("Expected an API error");
  } catch (error) {
    expect(error).toBeInstanceOf(ApiError);
    expect((error as ApiError).status).toBe(500);
    expect((error as Error).message).toBe(
      "Сервис временно недоступен. Повторите запрос позже.",
    );
  }
});
it("renders Russian status and field errors without changing protocol codes", () => {
  const state = "UP";
  expect(statusLabel(state)).toBe("Доступен (UP)");
  expect(state).toBe("UP");
  expect(
    validationError({
      loc: ["body", "interval_seconds"],
      type: "greater_than_equal",
      ctx: { ge: 30 },
    }),
  ).toBe("Интервал: Минимальное значение: 30");
});
it("localizes native required validation and clears custom validity on input", () => {
  installRussianValidation();
  document.body.innerHTML = '<input required type="email">';
  const input = document.querySelector("input")!;
  expect(input.checkValidity()).toBe(false);
  expect(input.validationMessage).toBe("Заполните это поле.");
  input.value = "owner@example.com";
  input.dispatchEvent(new Event("input", { bubbles: true }));
  expect(input.checkValidity()).toBe(true);
});
