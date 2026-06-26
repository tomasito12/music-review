export type SetupStep = "broad" | "details" | "filters";

export const SETUP_STEPS: ReadonlyArray<{ id: SetupStep; label: string }> = [
  { id: "broad", label: "1 Richtungen" },
  { id: "details", label: "2 Details" },
  { id: "filters", label: "3 Filter" },
];

const SETUP_STEP_ORDER: Record<SetupStep, number> = {
  broad: 0,
  details: 1,
  filters: 2,
};

export interface SetupStepNavigationContext {
  hasBroadSelection: boolean;
  hasDetailSelection: boolean;
}

/** Whether the progress bar may jump to another wizard step. */
export function canNavigateToSetupStep(
  current: SetupStep,
  target: SetupStep,
  context: SetupStepNavigationContext = {
    hasBroadSelection: false,
    hasDetailSelection: false,
  },
): boolean {
  const currentOrder = SETUP_STEP_ORDER[current];
  const targetOrder = SETUP_STEP_ORDER[target];
  if (targetOrder <= currentOrder) {
    return true;
  }
  if (target === "details" && context.hasBroadSelection) {
    return true;
  }
  if (target === "filters" && context.hasDetailSelection) {
    return true;
  }
  return false;
}
