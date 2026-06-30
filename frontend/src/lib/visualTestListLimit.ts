import type { Recommendation } from "../types";

import { isVisualTestMode } from "./visualTestMode";

/** Maximum list rows rendered during Playwright visual regression. */
export const VISUAL_TEST_LIST_ITEM_LIMIT = 8;

/** Trim long recommendation lists so screenshot height stays predictable. */
export function limitRecommendationsForVisualTest(
  recommendations: Recommendation[],
): Recommendation[] {
  if (
    !isVisualTestMode() ||
    recommendations.length <= VISUAL_TEST_LIST_ITEM_LIMIT
  ) {
    return recommendations;
  }
  return recommendations.slice(0, VISUAL_TEST_LIST_ITEM_LIMIT);
}
