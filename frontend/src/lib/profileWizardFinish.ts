import type { ProfileEntryContext } from "./profilePageEntry";
import type { SetupStep } from "./profileWizard";

export type WizardFinishAction = "finishSetup" | "returnToOverview";

/** Chooses whether wizard completion leaves the app or returns to overview. */
export function resolveWizardFinishAction(input: {
  entryContext: ProfileEntryContext;
  hasReturnRoute: boolean;
}): WizardFinishAction {
  if (input.entryContext === "initial" || input.entryContext === "shortcut") {
    return "finishSetup";
  }
  if (input.hasReturnRoute) {
    return "finishSetup";
  }
  return "returnToOverview";
}

/** Returns the primary button label for the active wizard step. */
export function resolveWizardPrimaryLabel(input: {
  step: SetupStep;
  entryContext: ProfileEntryContext;
  isSubmitting: boolean;
}): string {
  if (input.step === "broad") {
    return "Detailstile auswählen";
  }
  if (input.step === "details") {
    return "Filter und Gewichtung";
  }
  if (input.isSubmitting) {
    return "Empfehlungen werden geladen ...";
  }
  if (input.entryContext === "initial") {
    return "Empfehlungen anzeigen";
  }
  return "Fertig";
}
