import type { Recommendation, RecommendationHighlight } from "../types";

import type { ArtistImageData } from "./artistImageApi";
import { artistImageLookupKey } from "./artistImageLookupKey";

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
      if (lookupKey.length === 0 || claimedArtistLookupKeys.has(lookupKey)) {
        return false;
      }
      return hasPhoto(recommendation);
    });

    if (selectedRank !== undefined) {
      const recommendation = rankByNumber.get(selectedRank);
      if (recommendation !== undefined) {
        const lookupKey = recommendationArtistLookupKey(recommendation);
        if (lookupKey.length > 0) {
          claimedArtistLookupKeys.add(lookupKey);
        }
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

/** Artist lookup keys already shown in Entdecken highlight cards. */
export function entdeckenHighlightArtistLookupKeys(
  highlights: RecommendationHighlight[],
): Set<string> {
  return new Set(
    highlights
      .map((highlight) => recommendationArtistLookupKey(highlight.recommendation))
      .filter((lookupKey) => lookupKey.length > 0),
  );
}

/** Ranks used by Entdecken highlight cards (excluded from list photo slots). */
export function entdeckenHighlightRanks(
  highlights: RecommendationHighlight[],
): Set<number> {
  return new Set(highlights.map((highlight) => highlight.recommendation.rank));
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

  const addHighlight = (
    label: string,
    description: string,
    recommendation: Recommendation | undefined,
  ): void => {
    if (recommendation === undefined) {
      return;
    }
    const lookupKey = recommendationArtistLookupKey(recommendation);
    if (lookupKey.length === 0 || usedArtistLookupKeys.has(lookupKey)) {
      return;
    }
    usedArtistLookupKeys.add(lookupKey);
    highlights.push({ label, description, recommendation });
  };

  const pickTopUnused = (
    scoreFor: (item: Recommendation) => number,
    exclude: Recommendation | undefined = undefined,
  ): Recommendation | undefined => {
    const excludeAlbumKey = exclude === undefined ? null : albumKey(exclude);
    return [...recommendations]
      .filter((item) => {
        const lookupKey = recommendationArtistLookupKey(item);
        if (lookupKey.length === 0 || usedArtistLookupKeys.has(lookupKey)) {
          return false;
        }
        return excludeAlbumKey === null || albumKey(item) !== excludeAlbumKey;
      })
      .sort((left, right) => scoreFor(right) - scoreFor(left))[0];
  };

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
    "Hohe stilistische Vielfalt im Album.",
    pickTopUnused((item) => item.albumStyleBreadth),
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
