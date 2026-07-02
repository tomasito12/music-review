import type { PlaylistExportItem } from "./playlistExport";
import type { Recommendation } from "../types";

import { isVisualTestMode } from "./visualTestMode";

/** Maximum list rows rendered during Playwright visual regression. */
export const VISUAL_TEST_LIST_ITEM_LIMIT = 8;

/** Whether the load-more control should render for the current list state. */
export function shouldShowLoadMoreButton(canLoadMore: boolean): boolean {
  return canLoadMore && !isVisualTestMode();
}

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

/** Trim long playlist result lists so screenshot height stays predictable. */
export function limitPlaylistItemsForVisualTest(
  items: PlaylistExportItem[],
): PlaylistExportItem[] {
  if (!isVisualTestMode() || items.length <= VISUAL_TEST_LIST_ITEM_LIMIT) {
    return items;
  }
  return items.slice(0, VISUAL_TEST_LIST_ITEM_LIMIT);
}
