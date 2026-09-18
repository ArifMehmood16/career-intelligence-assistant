// Vite / TanStack Start config helper. Do not duplicate these plugins by hand
// or the app will break with duplicate registrations:
//   - TanStack Start, Vite React, Tailwind, tsconfig paths, Nitro
// You can pass additional config via defineConfig({ vite: { ... } }).
//
// @lovable.dev/vite-tanstack-config defaults the dev server to port 8080 (Lovable
// sandbox). Local `make run` and WEB_ORIGIN use 3000 — pin that here so the
// browser origin matches config/app.env and CSRF same-origin checks.
import { defineConfig } from "@lovable.dev/vite-tanstack-config";

const webPort = Number(process.env["WEB_PORT"] ?? "3000");

export default defineConfig({
  vite: {
    server: {
      host: "127.0.0.1",
      port: Number.isFinite(webPort) && webPort > 0 ? webPort : 3000,
      strictPort: true,
    },
  },
  tanstackStart: {
    // Redirect TanStack Start's bundled server entry to src/server.ts (our SSR error wrapper).
    // nitro/vite builds from this
    server: { entry: "server" },
  },
});
