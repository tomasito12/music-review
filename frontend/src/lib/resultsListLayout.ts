import type { RecommendationHighlight } from "../types";

/** Whether the tuning block belongs between highlights and the ranking list. */
export function shouldShowResultsListPrelude(
  highlights: RecommendationHighlight[],
): boolean {
  return highlights.length > 0;
}

/** Whether inline filters should render outside the prelude frame. */
export function shouldShowStandaloneFilterRegion(
  showFilterPanel: boolean,
  showPrelude: boolean,
): boolean {
  return showFilterPanel && !showPrelude;
}
