/// <reference types="vitest/config" />
import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";
import { serviceWorkerPlugin } from "./src/pwa/swPlugin.ts";

export default defineConfig({
  plugins: [react(), serviceWorkerPlugin()],
  server: {
    proxy: {
      "/api": "http://localhost:8000",
    },
  },
  test: {
    environment: "jsdom",
    globals: true,
    setupFiles: ["./src/test/setup.ts"],
    // Arkusze importowane z ?raw (testy reguł CSS, np. viewport.test.ts) mają zwracać treść, nie pusty stub.
    css: { include: /\?raw$/, modules: { classNameStrategy: "non-scoped" } },
  },
});
