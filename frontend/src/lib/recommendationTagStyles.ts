import type { CSSProperties } from "react";

import type { RecommendationTag } from "../types";

export const COMMUNITY_TAG_MIN_AFFINITY = 0.1;

/** Red scale aligned with Streamlit, without pink-heavy mid tones. */
const TAG_COLOR_STEPS = [
  { threshold: 0.65, background: "#7f1d1d", border: "#6b1515", color: "#fef2f2" },
  { threshold: 0.45, background: "#b91c1c", border: "#991b1b", color: "#fff5f5" },
  { threshold: 0.25, background: "#e57373", border: "#d46a6a", color: "#4a1414" },
  { threshold: 0.1, background: "#f5d5d5", border: "#e8b4b4", color: "#5c2020" },
  { threshold: 0.0, background: "#f3f4f6", border: "#e5e7eb", color: "#4b5563" },
] as const;

/** Keep tags that are strong enough to show on a card. */
export function visibleRecommendationTags(
  tags: RecommendationTag[],
): RecommendationTag[] {
  return tags.filter((tag) => tag.affinity >= COMMUNITY_TAG_MIN_AFFINITY);
}

/** Map album affinity to pill colors with readable contrast. */
export function recommendationTagStyle(tag: RecommendationTag): CSSProperties {
  const colors =
    TAG_COLOR_STEPS.find((step) => tag.affinity >= step.threshold) ??
    TAG_COLOR_STEPS[TAG_COLOR_STEPS.length - 1];

  return {
    backgroundColor: colors.background,
    borderColor: colors.border,
    color: colors.color,
  };
}

/** Shared inline style for the compact tag legend swatches. */
export function recommendationTagLegendSwatchStyle(
  affinity: number,
): CSSProperties {
  return recommendationTagStyle({
    label: "",
    affinity,
    matchesProfile: false,
  });
}
