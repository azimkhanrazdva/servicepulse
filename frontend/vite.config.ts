import { defineConfig } from "vitest/config";
export default defineConfig(({ mode }) => ({
  build: {
    rollupOptions: {
      input:
        mode === "public"
          ? { public: "public.html" }
          : { management: "index.html", public: "public.html" },
    },
  },
  server: { proxy: { "/api": "http://127.0.0.1:8000" } },
  test: { environment: "jsdom", include: ["src/**/*.test.{ts,tsx}"] },
}));
