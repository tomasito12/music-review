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

/** Whether the progress bar may jump to an earlier or current wizard step. */
export function canNavigateToSetupStep(
  current: SetupStep,
  target: SetupStep,
): boolean {
  return SETUP_STEP_ORDER[target] <= SETUP_STEP_ORDER[current];
}
