/** Bound the complete request, including response body parsing; abort on unmount or timeout. */
export async function withDeadline<T>(
  operation: (signal: AbortSignal) => Promise<T>,
  external?: AbortSignal,
  milliseconds = 15000,
): Promise<T> {
  const controller = new AbortController();
  let timer: ReturnType<typeof setTimeout>;
  let cancelled: () => void = () => {};
  const stop = new Promise<never>((_, reject) => {
    cancelled = () => {
      controller.abort();
      reject(new DOMException("Запрос отменён", "AbortError"));
    };
    timer = setTimeout(() => {
      controller.abort();
      reject(
        new Error(
          "Время ожидания истекло. Проверьте соединение и повторите запрос.",
        ),
      );
    }, milliseconds);
    if (external?.aborted) cancelled();
    else external?.addEventListener("abort", cancelled, { once: true });
  });
  try {
    return await Promise.race([operation(controller.signal), stop]);
  } catch (error) {
    if (error instanceof SyntaxError)
      throw new Error(
        "Получен некорректный ответ сервера. Повторите запрос позже.",
        { cause: error },
      );
    if (error instanceof TypeError)
      throw new Error(
        "Нет соединения с сервером. Проверьте сеть и повторите запрос.",
        { cause: error },
      );
    throw error;
  } finally {
    clearTimeout(timer!);
    external?.removeEventListener("abort", cancelled);
  }
}
