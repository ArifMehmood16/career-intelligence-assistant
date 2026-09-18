/**
 * Phase 12.4 — fixtures live under __fixtures__ for tests and /dev/states.
 * @vitest-environment node
 */
import { describe, expect, it } from "vitest";

import {
  cvFixture,
  providersFixture,
  rolesFixture,
} from "@/api/__fixtures__/fixtures";

describe("api fixtures location", () => {
  it("exports the gallery fixtures from __fixtures__", () => {
    expect(cvFixture.id).toBe("cv-1");
    expect(rolesFixture.length).toBeGreaterThan(0);
    expect(providersFixture.length).toBeGreaterThan(0);
  });
});
