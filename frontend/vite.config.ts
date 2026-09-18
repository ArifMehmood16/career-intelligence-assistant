// Vite / TanStack Start config helper. Do not duplicate these plugins by hand
// or the app will break with duplicate registrations:
//   - TanStack Start, Vite React, Tailwind, tsconfig paths, Nitro
// You can pass additional config via defineConfig({ vite: { ... } }).
import { defineConfig } from "@lovable.dev/vite-tanstack-config";

export default defineConfig({
  tanstackStart: {
    // Redirect TanStack Start's bundled server entry to src/server.ts (our SSR error wrapper).
    // nitro/vite builds from this
    server: { entry: "server" },
  },
});
