import { describe, expect, it } from "vitest";

import { canNavigateToSetupStep } from "./profileWizard";

describe("canNavigateToSetupStep", () => {
  it("allows navigating back to earlier steps", () => {
    expect(canNavigateToSetupStep("details", "broad")).toBe(true);
    expect(canNavigateToSetupStep("filters", "broad")).toBe(true);
    expect(canNavigateToSetupStep("filters", "details")).toBe(true);
  });

  it("blocks skipping forward", () => {
    expect(canNavigateToSetupStep("broad", "details")).toBe(false);
    expect(canNavigateToSetupStep("broad", "filters")).toBe(false);
    expect(canNavigateToSetupStep("details", "filters")).toBe(false);
  });
});
