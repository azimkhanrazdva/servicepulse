export function localDateTime(value: number) {
  const date = new Date(value);
  // Chromium canonicalizes zero seconds away; Playwright fill requires that form.
  return new Date(value - date.getTimezoneOffset() * 60000)
    .toISOString()
    .slice(0, 19)
    .replace(/:00$/, "");
}
