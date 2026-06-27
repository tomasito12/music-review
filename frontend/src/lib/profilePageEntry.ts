import type { ProfileSetupMode } from "./profileReturnNavigation";
import type { SetupStep } from "./profileWizard";

export type ProfilePageView = "overview" | "wizard";

export type ProfileEntryContext = "initial" | "overview" | "shortcut";

/** Picks overview vs. wizard when opening the Musikprofil route. */
export function resolveMusikprofilView(input: {
  hasProfile: boolean;
  setupMode: ProfileSetupMode;
  editStep: SetupStep | undefined;
}): ProfilePageView {
  if (!input.hasProfile) {
    return "wizard";
  }
  if (input.setupMode === "initial") {
    return "wizard";
  }
  if (input.editStep !== undefined) {
    return "wizard";
  }
  return "overview";
}

/** Maps how the wizard was opened to its entry context. */
export function resolveProfileEntryContext(input: {
  setupMode: ProfileSetupMode;
  wizardContext: ProfileEntryContext | null;
}): ProfileEntryContext {
  if (input.setupMode === "initial") {
    return "initial";
  }
  return input.wizardContext ?? "overview";
}
