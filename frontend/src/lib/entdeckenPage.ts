import type { Recommendation, RecommendationHighlight } from "../types";

import type { ArtistImageData } from "./artistImageApi";
import { artistImageLookupKey, claimArtist, isArtistClaimed } from "./artistImageLookupKey";
import { visibleRecommendationTags } from "./recommendationTagStyles";

/** Section copy for the Entdecken highlight hero. */
export const ENTDECKEN_HIGHLIGHTS_SECTION = {
  eyebrow: "Aus dem Archiv",
  title: "Deine Top-Fundstücke",
  intro:
    "Vier starke Einstiege mit Künstlerfotos — danach kannst du die Reihenfolge mit Filtern und Gewichtungen anpassen.",
} as const;

/** How many ranked archive rows to scan when picking photo highlights. */
export const ENTDECKEN_HIGHLIGHT_CANDIDATE_LIMIT = 200;

const FIRST_PHOTO_SLOT_CANDIDATES = [1, 2, 3, 4, 5] as const;
const RECURRING_PHOTO_ANCHOR_STEP = 6;

/** Candidate ranks for one recurring photo slot anchored at ``anchorRank``. */
export function recurringPhotoSlotCandidates(anchorRank: number): number[] {
  return [
    anchorRank,
    anchorRank + 1,
    anchorRank - 2,
    anchorRank + 2,
    anchorRank + 3,
  ];
}

/** Groups of ranks to try when placing photo tiles in the Entdecken list. */
export function entdeckenPhotoSlotGroups(
  maxRank: number,
  excludedRanks: ReadonlySet<number> = new Set(),
): number[][] {
  if (maxRank <= 0) {
    return [];
  }

  const groups: number[][] = [[...FIRST_PHOTO_SLOT_CANDIDATES]];
  for (
    let anchor = RECURRING_PHOTO_ANCHOR_STEP;
    anchor <= maxRank;
    anchor += RECURRING_PHOTO_ANCHOR_STEP
  ) {
    groups.push(recurringPhotoSlotCandidates(anchor));
  }
  return groups
    .map((group) => group.filter((rank) => !excludedRanks.has(rank)))
    .filter((group) => group.length > 0);
}

/** Pick ranks that should render as photo tiles once image availability is known. */
export function resolveEntdeckenPhotoRanks(
  recommendations: Recommendation[],
  hasPhoto: (recommendation: Recommendation) => boolean,
  excludedRanks: ReadonlySet<number> = new Set(),
  excludedArtistLookupKeys: ReadonlySet<string> = new Set(),
): Set<number> {
  if (recommendations.length === 0) {
    return new Set();
  }

  const rankByNumber = new Map(
    recommendations.map((recommendation) => [recommendation.rank, recommendation]),
  );
  const maxRank = Math.max(...recommendations.map((recommendation) => recommendation.rank));
  const photoRanks = new Set<number>();
  const claimedRanks = new Set<number>();
  const claimedArtistLookupKeys = new Set(excludedArtistLookupKeys);

  for (const candidates of entdeckenPhotoSlotGroups(maxRank, excludedRanks)) {
    const selectedRank = candidates.find((rank) => {
      if (claimedRanks.has(rank)) {
        return false;
      }
      const recommendation = rankByNumber.get(rank);
      if (recommendation === undefined) {
        return false;
      }
      const lookupKey = recommendationArtistLookupKey(recommendation);
      if (
        lookupKey.length === 0 ||
        isArtistClaimed(recommendationArtistClaimInput(recommendation), claimedArtistLookupKeys)
      ) {
        return false;
      }
      return hasPhoto(recommendation);
    });

    if (selectedRank !== undefined) {
      const recommendation = rankByNumber.get(selectedRank);
      if (recommendation !== undefined) {
        claimArtist(recommendationArtistClaimInput(recommendation), claimedArtistLookupKeys);
      }
      photoRanks.add(selectedRank);
      claimedRanks.add(selectedRank);
    }
  }

  return photoRanks;
}

/** Recommendations that may need artist images for Entdecken photo tiles. */
export function entdeckenPhotoLookupRecommendations(
  recommendations: Recommendation[],
  excludedRanks: ReadonlySet<number> = new Set(),
): Recommendation[] {
  if (recommendations.length === 0) {
    return [];
  }

  const rankByNumber = new Map(
    recommendations.map((recommendation) => [recommendation.rank, recommendation]),
  );
  const maxRank = Math.max(...recommendations.map((recommendation) => recommendation.rank));
  const candidateRanks = new Set<number>();

  for (const group of entdeckenPhotoSlotGroups(maxRank, excludedRanks)) {
    for (const rank of group) {
      candidateRanks.add(rank);
    }
  }

  return [...candidateRanks]
    .sort((left, right) => left - right)
    .map((rank) => rankByNumber.get(rank))
    .filter((recommendation): recommendation is Recommendation => recommendation !== undefined);
}

/** Kicker label for ranked photo tiles in the Entdecken list. */
export function formatRankPhotoKicker(rank: number): string {
  return `Platz ${rank.toString().padStart(2, "0")}`;
}

/** Category kicker for Entdecken highlight tiles, including archive rank. */
export function formatEntdeckenHighlightKicker(label: string, rank: number): string {
  return `${label} · ${formatRankPhotoKicker(rank)}`;
}

/** Stable artist key for Entdecken photo de-duplication. */
export function recommendationArtistLookupKey(recommendation: Recommendation): string {
  return artistImageLookupKey({
    artistMbid: recommendation.artistMbid,
    artistName: recommendation.artist,
  });
}

function recommendationArtistClaimInput(
  recommendation: Recommendation,
): { artistMbid?: string; artistName?: string } {
  return {
    artistMbid: recommendation.artistMbid,
    artistName: recommendation.artist,
  };
}

/** Artist dedupe keys already shown in Entdecken highlight cards. */
export function entdeckenHighlightArtistLookupKeys(
  highlights: RecommendationHighlight[],
): Set<string> {
  const keys = new Set<string>();
  for (const highlight of highlights) {
    claimArtist(recommendationArtistClaimInput(highlight.recommendation), keys);
  }
  return keys;
}

/** Ranks used by Entdecken highlight cards (excluded from list photo slots). */
export function entdeckenHighlightRanks(
  highlights: RecommendationHighlight[],
): Set<number> {
  return new Set(highlights.map((highlight) => highlight.recommendation.rank));
}

/** Effective style count (N_eff) from normalized tag affinities, matching backend Shannon logic. */
export function effectiveStyleCountFromAffinities(affinities: number[]): number {
  const positive = affinities.filter((affinity) => affinity > 0);
  if (positive.length <= 1) {
    return 1;
  }
  const total = positive.reduce((sum, affinity) => sum + affinity, 0);
  if (total <= 0) {
    return 1;
  }
  let entropy = 0;
  for (const affinity of positive) {
    const proportion = affinity / total;
    if (proportion > 0) {
      entropy -= proportion * Math.log(proportion);
    }
  }
  return Math.exp(entropy);
}

/** Style breadth from tags that are actually shown on recommendation cards. */
export function visibleStyleBreadthScore(recommendation: Recommendation): number {
  const tags = visibleRecommendationTags(recommendation.tags);
  if (tags.length <= 1) {
    return 1;
  }
  return effectiveStyleCountFromAffinities(tags.map((tag) => tag.affinity));
}

/** Count of style tags shown on the card (affinity at or above display threshold). */
export function visibleStyleTagCount(recommendation: Recommendation): number {
  return visibleRecommendationTags(recommendation.tags).length;
}

/** Derives four editorial Entdecken highlights from recommendations that have photos. */
export function selectEntdeckenHighlightsFromPhotoPool(
  recommendations: Recommendation[],
): RecommendationHighlight[] {
  if (recommendations.length === 0) {
    return [];
  }

  const usedArtistLookupKeys = new Set<string>();
  const highlights: RecommendationHighlight[] = [];

  const albumKey = (recommendation: Recommendation): string =>
    `${recommendation.artist}-${recommendation.album}`;

  const isArtistUsed = (recommendation: Recommendation): boolean =>
    isArtistClaimed(recommendationArtistClaimInput(recommendation), usedArtistLookupKeys);

  const markArtistUsed = (recommendation: Recommendation): void => {
    claimArtist(recommendationArtistClaimInput(recommendation), usedArtistLookupKeys);
  };

  const addHighlight = (
    label: string,
    description: string,
    recommendation: Recommendation | undefined,
  ): void => {
    if (recommendation === undefined) {
      return;
    }
    if (
      recommendationArtistLookupKey(recommendation).length === 0 ||
      isArtistUsed(recommendation)
    ) {
      return;
    }
    markArtistUsed(recommendation);
    highlights.push({ label, description, recommendation });
  };

  const pickTopUnused = (
    scoreFor: (item: Recommendation) => number,
    exclude: Recommendation | undefined = undefined,
    predicate: (item: Recommendation) => boolean = () => true,
  ): Recommendation | undefined => {
    const excludeAlbumKey = exclude === undefined ? null : albumKey(exclude);
    return [...recommendations]
      .filter((item) => {
        if (
          recommendationArtistLookupKey(item).length === 0 ||
          isArtistUsed(item)
        ) {
          return false;
        }
        if (!predicate(item)) {
          return false;
        }
        return excludeAlbumKey === null || albumKey(item) !== excludeAlbumKey;
      })
      .sort((left, right) => scoreFor(right) - scoreFor(left))[0];
  };

  const pickBroadestVisibleStyle = (): Recommendation | undefined =>
    pickTopUnused(
      (item) => visibleStyleBreadthScore(item),
      undefined,
      (item) => visibleStyleTagCount(item) >= 2,
    );

  const bestOverall = pickTopUnused((item) => item.score);
  addHighlight(
    "Beste Gesamtpassung",
    "Der stärkste Gesamtscore aus Passung, Wertung und Stilbreite.",
    bestOverall,
  );

  addHighlight(
    "Kritikerfavorit",
    "Besonders hoch bewertet bei plattentests.de.",
    pickTopUnused((item) => item.rating, bestOverall),
  );

  addHighlight(
    "Stilistisch breit",
    "Mehrere sichtbare Stil-Tags – verschiedene Richtungen auf einen Blick.",
    pickBroadestVisibleStyle(),
  );

  addHighlight(
    "Höchste Passung",
    "Die stärkste Stilpassung zu deinem Musikprofil.",
    pickTopUnused((item) => item.styleFit),
  );

  return highlights;
}

/** Archive-specific header copy for the Entdecken results page. */
export function buildEntdeckenHeaderMessage(total: number, loadedCount: number): string {
  if (total === 0) {
    return "Im Archiv liegt gerade nichts Passendes für dein Musikprofil.";
  }
  if (loadedCount >= total) {
    return `${total} Alben passen zu deinem Musikprofil und werden angezeigt.`;
  }
  return `${total} Alben passen zu deinem Musikprofil. ${loadedCount} werden gerade angezeigt.`;
}

/** Return whether a recommendation has a loaded artist photo for Entdecken tiles. */
export function entdeckenRecommendationHasPhoto(
  recommendation: Recommendation,
  imagesByLookupKey: Map<string, ArtistImageData | null>,
): boolean {
  const lookupKey = artistImageLookupKey({
    artistMbid: recommendation.artistMbid,
    artistName: recommendation.artist,
  });
  if (lookupKey.length === 0) {
    return false;
  }
  return imagesByLookupKey.get(lookupKey) != null;
}

/** First alternating photo-tile index after the optional rank-1 lead entry. */
export function entdeckenPhotoTileStartIndex(
  recommendations: Recommendation[],
  photoRanks: Set<number>,
): number {
  return recommendations.some(
    (recommendation) => recommendation.rank === 1 && photoRanks.has(1),
  )
    ? 1
    : 0;
}

/** Build display indices for alternating Entdecken photo tiles in list order. */
export function buildEntdeckenPhotoTileIndices(
  recommendations: Recommendation[],
  photoRanks: Set<number>,
): Map<number, number> {
  const indices = new Map<number, number>();
  let nextIndex = entdeckenPhotoTileStartIndex(recommendations, photoRanks);
  for (const recommendation of recommendations) {
    if (photoRanks.has(recommendation.rank)) {
      indices.set(recommendation.rank, nextIndex);
      nextIndex += 1;
    }
  }
  return indices;
}
