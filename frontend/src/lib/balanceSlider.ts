/** Returns fill widths for a bipolar balance slider track. */
export function balanceFillPercents(
  value: number,
  min = -1,
  max = 1,
): { left: number; right: number } {
  const clamped = Math.min(max, Math.max(min, value));
  const halfSpan = (max - min) / 2;
  return {
    left: clamped < 0 ? (-clamped / halfSpan) * 50 : 0,
    right: clamped > 0 ? (clamped / halfSpan) * 50 : 0,
  };
}

/** Snaps a balance value to the configured step. */
export function snapBalanceValue(value: number, step = 0.1, min = -1, max = 1): number {
  const snapped = Math.round(value / step) * step;
  return Math.min(max, Math.max(min, Number(snapped.toFixed(2))));
}
