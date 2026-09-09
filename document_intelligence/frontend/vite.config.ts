import { fileURLToPath, URL } from "node:url";

import tailwindcss from "@tailwindcss/vite";
import react from "@vitejs/plugin-react";
// From vitest/config rather than vite so the `test` block is typed.
import { defineConfig } from "vitest/config";

const BACKEND_ORIGIN = process.env.DI_BACKEND_ORIGIN ?? "http://127.0.0.1:8000";

export default defineConfig({
  plugins: [react(), tailwindcss()],
  resolve: {
    alias: { "@": fileURLToPath(new URL("./src", import.meta.url)) },
  },
  server: {
    port: 5173,
    proxy: {
      // Proxied rather than called cross-origin so the SSE stream and the
      // uploads share the page's origin, and no CORS layer is needed.
      "/api": { target: BACKEND_ORIGIN, changeOrigin: true },
      "/mock": { target: BACKEND_ORIGIN, changeOrigin: true },
    },
  },
  test: {
    environment: "jsdom",
    globals: true,
    setupFiles: ["./src/test/setup.ts"],
    css: true,
  },
});
