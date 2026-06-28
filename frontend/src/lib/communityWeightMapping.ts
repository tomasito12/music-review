/** Neutral stored weight used when no per-style bias was set. */
export const DEFAULT_COMMUNITY_WEIGHT_RAW = 0.5;

/** Converts a UI bias in [-1, 1] to a stored weight in [0, 1]. */
export function communityWeightStoredFromBias(bias: number): number {
  const clamped = Math.min(1, Math.max(-1, bias));
  return (clamped + 1) / 2;
}

/** Converts a stored weight in [0, 1] to a UI bias in [-1, 1]. */
export function communityWeightBiasFromStored(stored: number): number {
  const clamped = Math.min(1, Math.max(0, stored));
  return 2 * clamped - 1;
}

/** Keeps only weights for selected communities with neutral defaults. */
export function normalizeCommunityWeights(
  selectedCommunityIds: string[],
  weights: Record<string, number>,
): Record<string, number> {
  const pruned = pruneCommunityWeights(selectedCommunityIds, weights);
  const withDefaults = Object.fromEntries(
    selectedCommunityIds.map((communityId) => [
      communityId,
      pruned[communityId] ?? DEFAULT_COMMUNITY_WEIGHT_RAW,
    ]),
  );
  return migrateLegacyCommunityWeights(withDefaults);
}

/** Maps the old frontend default weight of 1.0 back to neutral. */
export function migrateLegacyCommunityWeights(
  weights: Record<string, number>,
): Record<string, number> {
  const values = Object.values(weights);
  if (values.length === 0) {
    return weights;
  }
  const usesLegacyDefault = values.every((weight) => weight === 1);
  if (!usesLegacyDefault) {
    return weights;
  }
  return Object.fromEntries(
    Object.keys(weights).map((communityId) => [
      communityId,
      DEFAULT_COMMUNITY_WEIGHT_RAW,
    ]),
  );
}

/** Drops weights for communities that are no longer selected. */
export function pruneCommunityWeights(
  selectedCommunityIds: string[],
  weights: Record<string, number>,
): Record<string, number> {
  const selected = new Set(selectedCommunityIds);
  return Object.fromEntries(
    Object.entries(weights).filter(([communityId]) => selected.has(communityId)),
  );
}

/** Updates one community weight from a UI bias slider. */
export function updateCommunityWeightBias(
  weights: Record<string, number>,
  communityId: string,
  bias: number,
): Record<string, number> {
  return {
    ...weights,
    [communityId]: communityWeightStoredFromBias(bias),
  };
}
