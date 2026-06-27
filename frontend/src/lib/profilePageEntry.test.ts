import { describe, expect, it } from "vitest";

import {
  resolveMusikprofilView,
  resolveProfileEntryContext,
} from "./profilePageEntry";

describe("resolveMusikprofilView", () => {
  it("opens the wizard when no profile exists", () => {
    expect(
      resolveMusikprofilView({
        hasProfile: false,
        setupMode: "edit",
        editStep: undefined,
      }),
    ).toBe("wizard");
  });

  it("opens the wizard during first-time setup", () => {
    expect(
      resolveMusikprofilView({
        hasProfile: true,
        setupMode: "initial",
        editStep: undefined,
      }),
    ).toBe("wizard");
  });

  it("opens the wizard when a specific edit step is requested", () => {
    expect(
      resolveMusikprofilView({
        hasProfile: true,
        setupMode: "edit",
        editStep: "filters",
      }),
    ).toBe("wizard");
  });

  it("opens the overview for returning users", () => {
    expect(
      resolveMusikprofilView({
        hasProfile: true,
        setupMode: "edit",
        editStep: undefined,
      }),
    ).toBe("overview");
  });
});

describe("resolveProfileEntryContext", () => {
  it("uses initial context during first-time setup", () => {
    expect(
      resolveProfileEntryContext({
        setupMode: "initial",
        wizardContext: "shortcut",
      }),
    ).toBe("initial");
  });

  it("falls back to overview when no wizard context is stored", () => {
    expect(
      resolveProfileEntryContext({
        setupMode: "edit",
        wizardContext: null,
      }),
    ).toBe("overview");
  });
});
