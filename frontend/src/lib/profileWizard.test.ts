import { describe, expect, it } from "vitest";

import { canNavigateToSetupStep } from "./profileWizard";

describe("canNavigateToSetupStep", () => {
  it("allows navigating back to earlier steps", () => {
    expect(canNavigateToSetupStep("details", "broad")).toBe(true);
    expect(canNavigateToSetupStep("filters", "broad")).toBe(true);
    expect(canNavigateToSetupStep("filters", "details")).toBe(true);
  });

  it("blocks skipping forward without prior selections", () => {
    expect(canNavigateToSetupStep("broad", "details")).toBe(false);
    expect(canNavigateToSetupStep("broad", "filters")).toBe(false);
    expect(canNavigateToSetupStep("details", "filters")).toBe(false);
  });

  it("allows returning to details when broad categories are already selected", () => {
    expect(
      canNavigateToSetupStep("broad", "details", { hasBroadSelection: true, hasDetailSelection: false }),
    ).toBe(true);
  });

  it("allows returning to filters when detail styles are already selected", () => {
    expect(
      canNavigateToSetupStep("broad", "filters", {
        hasBroadSelection: true,
        hasDetailSelection: true,
      }),
    ).toBe(true);
  });
});
