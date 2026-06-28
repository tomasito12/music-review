import type { Recommendation } from "../types";

import type { ArtistImageData } from "./artistImageApi";
import { artistImageLookupKey } from "./artistImageLookupKey";

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
export function entdeckenPhotoSlotGroups(maxRank: number): number[][] {
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
  return groups;
}

/** Pick ranks that should render as photo tiles once image availability is known. */
export function resolveEntdeckenPhotoRanks(
  recommendations: Recommendation[],
  hasPhoto: (recommendation: Recommendation) => boolean,
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

  for (const candidates of entdeckenPhotoSlotGroups(maxRank)) {
    const selectedRank = candidates.find((rank) => {
      if (claimedRanks.has(rank)) {
        return false;
      }
      const recommendation = rankByNumber.get(rank);
      if (recommendation === undefined) {
        return false;
      }
      return hasPhoto(recommendation);
    });

    if (selectedRank !== undefined) {
      photoRanks.add(selectedRank);
      claimedRanks.add(selectedRank);
    }
  }

  return photoRanks;
}

/** Recommendations that may need artist images for Entdecken photo tiles. */
export function entdeckenPhotoLookupRecommendations(
  recommendations: Recommendation[],
): Recommendation[] {
  if (recommendations.length === 0) {
    return [];
  }

  const rankByNumber = new Map(
    recommendations.map((recommendation) => [recommendation.rank, recommendation]),
  );
  const maxRank = Math.max(...recommendations.map((recommendation) => recommendation.rank));
  const candidateRanks = new Set<number>();

  for (const group of entdeckenPhotoSlotGroups(maxRank)) {
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
