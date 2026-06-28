import { sortModeLabel, styleMatchMinPercent } from "./filterControls";
import type { TasteCommunityOption } from "./plattenradarApi";
import type { ProfileSetupResult } from "./profileSessionStorage";

export const DETAIL_STYLE_PREVIEW_COUNT = 5;

export interface ProfileOverviewSummary {
  broadCategories: string[];
  broadCategoriesText: string;
  detailStyleCount: number;
  detailStylePreview: string[];
  detailStyleOverflow: number;
  detailStylesText: string;
  presetLabel: string;
  filterChips: string[];
}

/** Derives broad categories for the selected detail communities. */
export function deriveBroadCategories(
  selectedCommunityIds: string[],
  communities: TasteCommunityOption[],
): string[] {
  return Array.from(
    new Set(
      communities
        .filter((community) => selectedCommunityIds.includes(community.id))
        .flatMap((community) => community.broad_categories),
    ),
  ).sort((left, right) => left.localeCompare(right, "de"));
}

/** Builds readable overview copy for the Musikprofil summary cards. */
export function buildProfileOverviewSummary(
  session: ProfileSetupResult,
  communities: TasteCommunityOption[],
): ProfileOverviewSummary {
  const { profile } = session;
  const broadCategories = deriveBroadCategories(
    profile.selected_communities,
    communities,
  );
  const selectedCommunities = communities
    .filter((community) => profile.selected_communities.includes(community.id))
    .sort((left, right) => left.label.localeCompare(right.label, "de"));
  const detailStylePreview = selectedCommunities
    .slice(0, DETAIL_STYLE_PREVIEW_COUNT)
    .map((community) => community.label);
  const detailStyleOverflow = Math.max(
    0,
    selectedCommunities.length - detailStylePreview.length,
  );
  const detailStylesText = formatDetailStylesText(
    selectedCommunities.length,
    detailStylePreview,
    detailStyleOverflow,
  );

  return {
    broadCategories,
    broadCategoriesText:
      broadCategories.length > 0
        ? broadCategories.join(", ")
        : "Noch keine Richtungen gewählt",
    detailStyleCount: selectedCommunities.length,
    detailStylePreview,
    detailStyleOverflow,
    detailStylesText,
    presetLabel: session.presetLabel,
    filterChips: buildProfileOverviewFilterChips(session),
  };
}

function formatDetailStylesText(
  count: number,
  preview: string[],
  overflow: number,
): string {
  if (count === 0) {
    return "Noch keine Detailstile gewählt";
  }
  if (preview.length === 0) {
    return `${count} Detailstile`;
  }
  const previewText = preview.join(", ");
  if (overflow > 0) {
    return `${count} Detailstile: ${previewText}, +${overflow} weitere`;
  }
  return `${count} Detailstile: ${previewText}`;
}

function buildProfileOverviewFilterChips(session: ProfileSetupResult): string[] {
  const { filter_settings: filters } = session.profile;
  const chips = [
    session.presetLabel,
    `Stilpassung mindestens ${styleMatchMinPercent(filters)} %`,
    `Wertung ${filters.rating_min}–${filters.rating_max}`,
    sortModeLabel(filters.sort_mode),
  ];
  if (filters.serendipity > 0) {
    chips.push("Mit Zufall in der Sortierung");
  }
  return chips;
}
