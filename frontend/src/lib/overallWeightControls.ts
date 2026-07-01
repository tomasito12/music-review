import type { TasteFilterSettings } from "./plattenradarApi";

export const OVERALL_WEIGHT_FIELDS = [
  "overall_weight_alpha",
  "overall_weight_beta",
  "overall_weight_gamma",
] as const;

export type OverallWeightField = (typeof OVERALL_WEIGHT_FIELDS)[number];

/** Return normalized share fractions for the three overall-score weights. */
export function normalizedOverallShares(settings: TasteFilterSettings): number[] {
  const raw = OVERALL_WEIGHT_FIELDS.map((field) =>
    Math.max(0, settings[field]),
  );
  const total = raw.reduce((sum, value) => sum + value, 0);
  if (total <= 0) {
    return [1 / 3, 1 / 3, 1 / 3];
  }
  return raw.map((value) => value / total);
}

/** Update one weight share and redistribute the remainder across the other two. */
export function updateOverallWeightShare(
  settings: TasteFilterSettings,
  field: OverallWeightField,
  sharePercent: number,
): TasteFilterSettings {
  const shares = normalizedOverallShares(settings);
  const fieldIndex = OVERALL_WEIGHT_FIELDS.indexOf(field);
  const boundedShare = Math.min(100, Math.max(0, sharePercent)) / 100;
  const otherIndices = OVERALL_WEIGHT_FIELDS.map((_, index) => index).filter(
    (index) => index !== fieldIndex,
  );
  const otherSum = otherIndices.reduce((sum, index) => sum + shares[index], 0);
  const nextShares = [...shares];
  nextShares[fieldIndex] = boundedShare;

  const remaining = 1 - boundedShare;
  if (otherSum > 0) {
    for (const index of otherIndices) {
      nextShares[index] = (shares[index] / otherSum) * remaining;
    }
  } else {
    const each = remaining / otherIndices.length;
    for (const index of otherIndices) {
      nextShares[index] = each;
    }
  }

  return {
    ...settings,
    overall_weight_alpha: nextShares[0],
    overall_weight_beta: nextShares[1],
    overall_weight_gamma: nextShares[2],
  };
}

/** Convert normalized shares to whole-number percents that sum to 100. */
export function overallSharePercents(settings: TasteFilterSettings): number[] {
  const shares = normalizedOverallShares(settings);
  const percents = shares.map((share) => Math.round(share * 100));
  const drift = 100 - percents.reduce((sum, value) => sum + value, 0);
  if (drift !== 0) {
    const maxIndex = percents.indexOf(Math.max(...percents));
    percents[maxIndex] += drift;
  }
  return percents;
}
