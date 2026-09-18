/**
 * Local make run uses port 3000; Lovable's helper otherwise defaults to 8080.
 * @vitest-environment node
 */
import { readFileSync } from "node:fs";
import path from "node:path";
import { fileURLToPath } from "node:url";
import { describe, expect, it } from "vitest";

const configPath = path.join(
  path.dirname(fileURLToPath(import.meta.url)),
  "../vite.config.ts",
);

describe("vite.dev server port", () => {
  it("pins the local host port to 3000 (WEB_PORT override allowed)", () => {
    const source = readFileSync(configPath, "utf8");
    expect(source).toMatch(/WEB_PORT/);
    expect(source).toMatch(/port:\s*Number\.isFinite\(webPort\)/);
    expect(source).toMatch(/"3000"/);
    expect(source).toMatch(/strictPort:\s*true/);
  });
});
