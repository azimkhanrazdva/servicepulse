/** Russian presentation only: persisted values, API fields and enum codes are unchanged. */
const labels: Record<string, string> = {
  UP: "Доступен (UP)",
  DOWN: "Недоступен (DOWN)",
  UNKNOWN: "Нет наблюдений (UNKNOWN)",
  PAUSED: "На паузе (PAUSED)",
  OPEN: "Открыт (OPEN)",
  CLOSED: "Закрыт (CLOSED)",
  RECOVERED: "Восстановлен (RECOVERED)",
  RECOVERY: "Восстановление (RECOVERY)",
  CONFIG_CHANGED: "Изменены настройки (CONFIG_CHANGED)",
  ACTIVE: "Действует (ACTIVE)",
  UPCOMING: "Запланировано (UPCOMING)",
  ENDED: "Завершено (ENDED)",
  PENDING: "Ожидает отправки (PENDING)",
  INFLIGHT: "Отправляется (INFLIGHT)",
  SENT: "Принято SMTP (SENT)",
  FAILED: "Ошибка доставки (FAILED)",
  CANCELLED: "Отменено (CANCELLED)",
  blocked_destination: "Адрес запрещён политикой безопасности",
  timeout: "Превышен таймаут",
  network_error: "Сетевая ошибка",
  unexpected_status: "Неожиданный HTTP-код",
  body_mismatch: "Ожидаемый текст не найден",
  body_too_large: "Превышен размер ответа",
  encoded_response: "Сжатый ответ не поддерживается",
  invalid_response: "Некорректный ответ",
  smtp_temporary: "Временный отказ SMTP",
  smtp_permanent: "Постоянный отказ SMTP",
  smtp_network: "Нет соединения с SMTP",
  smtp_timeout: "Истёк таймаут SMTP",
  retry_exhausted: "Попытки отправки исчерпаны",
  invalid_message: "Некорректное письмо",
};
export const statusLabel = (value: string) => labels[value] ?? value;
export const reasonLabel = (value: string | null) =>
  value ? (labels[value] ?? "Неизвестная причина") : "—";
export const periodLabel = (value: string) =>
  ({ "24h": "24 ч", "7d": "7 дней", "30d": "30 дней" })[value] ?? value;
export const sectionLabel = (value: string) =>
  ({
    overview: "Обзор",
    monitors: "Все мониторы",
    groups: "Группы",
    incidents: "Инциденты",
    maintenance: "Обслуживание",
    notifications: "Уведомления",
    publication: "Публичные страницы",
  })[value] ?? "Обзор";

const fields: Record<string, string> = {
  name: "Название",
  url: "URL",
  interval_seconds: "Интервал",
  timeout_seconds: "Таймаут",
  expected_status: "Ожидаемый HTTP-код",
  expected_body: "Ожидаемый текст",
  failure_threshold: "Порог ошибок",
  recipients: "Получатели",
  monitor_ids: "Мониторы",
  start_at: "Начало",
  end_at: "Окончание",
  slug: "Адрес страницы",
  title: "Заголовок",
  public_name: "Публичное название",
  config_version: "Версия настроек",
};
export function requestError(status: number) {
  if (status === 409)
    return "Данные изменились или операция уже выполняется. Обновите данные перед повторной попыткой; черновик сохранён.";
  if (status === 404) return "Объект не найден или доступ к нему отозван.";
  if (status === 422) return "Проверьте значения полей формы.";
  if (status >= 500)
    return "Сервис временно недоступен. Повторите запрос позже.";
  return `Не удалось выполнить запрос (HTTP ${status}).`;
}
export function validationError(issue: {
  loc: (string | number)[];
  type?: string;
  msg?: string;
  ctx?: Record<string, unknown>;
}) {
  const field = issue.loc
    .slice(1)
    .map(
      (v) =>
        fields[String(v)] ?? (typeof v === "number" ? String(v + 1) : "Поле"),
    )
    .join(" · ");
  const kind = issue.type ?? "";
  const bound = issue.ctx;
  let message = "Недопустимое значение";
  if (kind === "missing") message = "Обязательное поле";
  else if (kind === "greater_than_equal")
    message = `Минимальное значение: ${bound?.ge}`;
  else if (kind === "less_than_equal")
    message = `Максимальное значение: ${bound?.le}`;
  else if (kind.includes("too_long")) message = "Превышена допустимая длина";
  else if (kind.includes("too_short")) message = "Недостаточная длина";
  else if (kind.includes("url")) message = "Укажите корректный HTTP(S) URL";
  else if (kind.includes("int") || kind.includes("float"))
    message = "Укажите число";
  else if (issue.msg?.toLowerCase().includes("email"))
    message = "Укажите корректный адрес электронной почты";
  return `${field}: ${message}`;
}

export function installRussianValidation() {
  document.addEventListener(
    "invalid",
    (event) => {
      const field = event.target;
      if (!(
        field instanceof HTMLInputElement ||
        field instanceof HTMLSelectElement ||
        field instanceof HTMLTextAreaElement
      ))
        return;
      const v = field.validity;
      const message = v.valueMissing
        ? "Заполните это поле."
        : v.typeMismatch
          ? "Проверьте формат значения."
          : v.rangeUnderflow
            ? "Значение меньше допустимого."
            : v.rangeOverflow
              ? "Значение больше допустимого."
              : v.stepMismatch
                ? "Укажите значение с допустимым шагом."
                : v.patternMismatch
                  ? "Значение не соответствует требуемому формату."
                  : "Проверьте значение поля.";
      field.setCustomValidity(message);
    },
    true,
  );
  document.addEventListener("input", (event) => {
    const field = event.target;
    if (
      field instanceof HTMLInputElement ||
      field instanceof HTMLSelectElement ||
      field instanceof HTMLTextAreaElement
    )
      field.setCustomValidity("");
  });
}
