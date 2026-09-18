/**
 * Design and fixture guards — prove the ESLint rules fail closed.
 * PLAN 1.8 / 12.4: no hex / raw Tailwind palette in components; no fixture
 * imports outside tests and /dev/states.
 */
import path from "node:path";
import { fileURLToPath } from "node:url";
import { ESLint } from "eslint";
import { describe, expect, it } from "vitest";

const frontendRoot = path.resolve(
  path.dirname(fileURLToPath(import.meta.url)),
  "../..",
);

async function lintVirtual(filePath: string, code: string) {
  const eslint = new ESLint({ cwd: frontendRoot });
  const [result] = await eslint.lintText(code, { filePath });
  return result;
}

describe("frontend design guards", () => {
  it("rejects a hex colour in a component className", async () => {
    const result = await lintVirtual(
      path.join(frontendRoot, "src/components/offender.tsx"),
      `export function Offender() {\n  return <div className="text-[#ff0000]" />;\n}\n`,
    );
    expect(result?.errorCount ?? 0).toBeGreaterThan(0);
    expect(JSON.stringify(result?.messages ?? [])).toMatch(
      /hex|design token|palette/i,
    );
  });

  it("rejects a raw Tailwind palette class in a component", async () => {
    const result = await lintVirtual(
      path.join(frontendRoot, "src/components/offender.tsx"),
      `export function Offender() {\n  return <div className="bg-gray-100" />;\n}\n`,
    );
    expect(result?.errorCount ?? 0).toBeGreaterThan(0);
  });

  it("rejects a legacy fixture import from a component", async () => {
    const result = await lintVirtual(
      path.join(frontendRoot, "src/components/offender.tsx"),
      `import { rolesFixture } from "@/api/fixtures";\nexport function Offender() {\n  return <div>{rolesFixture.length}</div>;\n}\n`,
    );
    expect(result?.errorCount ?? 0).toBeGreaterThan(0);
    expect(JSON.stringify(result?.messages ?? [])).toMatch(/fixture/i);
  });

  it("rejects an __fixtures__ import from a component", async () => {
    const result = await lintVirtual(
      path.join(frontendRoot, "src/components/offender.tsx"),
      `import { rolesFixture } from "@/api/__fixtures__/fixtures";\nexport function Offender() {\n  return <div>{rolesFixture.length}</div>;\n}\n`,
    );
    expect(result?.errorCount ?? 0).toBeGreaterThan(0);
    expect(JSON.stringify(result?.messages ?? [])).toMatch(/fixture/i);
  });
});
