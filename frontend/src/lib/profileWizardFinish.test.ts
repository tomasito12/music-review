import { describe, expect, it } from "vitest";

import {
  resolveWizardFinishAction,
  resolveWizardPrimaryLabel,
} from "./profileWizardFinish";

describe("resolveWizardFinishAction", () => {
  it("keeps first-time setup on the finish flow", () => {
    expect(
      resolveWizardFinishAction({
        entryContext: "initial",
        hasReturnRoute: false,
      }),
    ).toBe("finishSetup");
  });

  it("returns to the origin page for shortcut edits", () => {
    expect(
      resolveWizardFinishAction({
        entryContext: "shortcut",
        hasReturnRoute: true,
      }),
    ).toBe("finishSetup");
  });

  it("returns to overview when editing from the overview without a return route", () => {
    expect(
      resolveWizardFinishAction({
        entryContext: "overview",
        hasReturnRoute: false,
      }),
    ).toBe("returnToOverview");
  });
});

describe("resolveWizardPrimaryLabel", () => {
  it("uses recommendation copy for first-time setup", () => {
    expect(
      resolveWizardPrimaryLabel({
        step: "filters",
        entryContext: "initial",
        isSubmitting: false,
      }),
    ).toBe("Empfehlungen anzeigen");
  });

  it("uses Fertig for profile edits", () => {
    expect(
      resolveWizardPrimaryLabel({
        step: "filters",
        entryContext: "overview",
        isSubmitting: false,
      }),
    ).toBe("Fertig");
  });
});
