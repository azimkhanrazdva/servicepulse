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
      reject(new DOMException("Request cancelled", "AbortError"));
    };
    timer = setTimeout(() => {
      controller.abort();
      reject(new Error("Request timed out. Check your connection and retry."));
    }, milliseconds);
    if (external?.aborted) cancelled();
    else external?.addEventListener("abort", cancelled, { once: true });
  });
  try {
    return await Promise.race([operation(controller.signal), stop]);
  } finally {
    clearTimeout(timer!);
    external?.removeEventListener("abort", cancelled);
  }
}
