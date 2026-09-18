import js from "@eslint/js";
import eslintPluginPrettier from "eslint-plugin-prettier/recommended";
import globals from "globals";
import reactHooks from "eslint-plugin-react-hooks";
import reactRefresh from "eslint-plugin-react-refresh";
import tseslint from "typescript-eslint";
import designTokens from "./eslint/design-tokens.mjs";

export default tseslint.config(
  { ignores: ["dist", ".output", ".vinxi", "coverage"] },
  {
    extends: [js.configs.recommended, ...tseslint.configs.recommended],
    files: ["**/*.{ts,tsx}"],
    languageOptions: {
      ecmaVersion: 2020,
      globals: globals.browser,
    },
    plugins: {
      "react-hooks": reactHooks,
      "react-refresh": reactRefresh,
    },
    rules: {
      ...reactHooks.configs.recommended.rules,
      "no-restricted-imports": [
        "error",
        {
          paths: [
            {
              name: "server-only",
              message:
                "TanStack Start does not use the Next.js `server-only` package. Rename the module to `*.server.ts` or mark it with `@tanstack/react-start/server-only`.",
            },
          ],
        },
      ],
      "react-refresh/only-export-components": [
        "warn",
        {
          allowConstantExport: true,
          // shadcn Button co-exports CVA variants for composition (alert-dialog, settings).
          allowExportNames: ["buttonVariants"],
        },
      ],
      "@typescript-eslint/no-unused-vars": "off",
    },
  },
  {
    files: ["src/components/**/*.{ts,tsx}"],
    ignores: ["src/components/**/*.{test,spec}.{ts,tsx}"],
    plugins: {
      "career-design": designTokens,
    },
    rules: {
      "career-design/no-raw-design-tokens": "error",
    },
  },
  {
    files: ["src/**/*.{ts,tsx}"],
    ignores: [
      "src/**/*.{test,spec}.{ts,tsx}",
      "src/test/**",
      "src/api/client.ts",
      "src/api/fixtures.ts",
      "src/routes/dev.states.tsx",
    ],
    rules: {
      "no-restricted-imports": [
        "error",
        {
          paths: [
            {
              name: "server-only",
              message:
                "TanStack Start does not use the Next.js `server-only` package. Rename the module to `*.server.ts` or mark it with `@tanstack/react-start/server-only`.",
            },
            {
              name: "@/api/fixtures",
              message:
                "Fixtures belong in tests and /dev/states, not production UI modules.",
            },
            {
              name: "./fixtures",
              message:
                "Fixtures belong in tests and /dev/states, not production UI modules.",
            },
            {
              name: "../fixtures",
              message:
                "Fixtures belong in tests and /dev/states, not production UI modules.",
            },
          ],
          patterns: [
            {
              group: ["**/__fixtures__/**", "**/fixtures.ts"],
              message:
                "Fixtures belong in tests and /dev/states, not production UI modules.",
            },
          ],
        },
      ],
    },
  },
  eslintPluginPrettier,
);
