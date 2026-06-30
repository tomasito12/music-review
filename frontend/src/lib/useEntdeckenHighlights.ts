import { useMemo } from "react";

import type { ArtistImageData } from "./artistImageApi";
import { artistImageLookupKey } from "./artistImageLookupKey";
import {
  ENTDECKEN_HIGHLIGHT_CANDIDATE_LIMIT,
  entdeckenRecommendationHasPhoto,
  selectEntdeckenHighlightsFromPhotoPool,
} from "./entdeckenPage";
import { useArtistImagesBatch } from "./useArtistImagesBatch";
import type { Recommendation, RecommendationHighlight } from "../types";

export interface UseEntdeckenHighlightsResult {
  highlights: RecommendationHighlight[];
  imagesByLookupKey: Map<string, ArtistImageData | null>;
  loading: boolean;
}

/** Resolve photo-backed Entdecken highlights from the top-ranked archive window. */
export function useEntdeckenHighlights(
  recommendations: Recommendation[],
): UseEntdeckenHighlightsResult {
  const candidates = useMemo(
    () => recommendations.slice(0, ENTDECKEN_HIGHLIGHT_CANDIDATE_LIMIT),
    [recommendations],
  );
  const { imagesByLookupKey, loading } = useArtistImagesBatch(
    candidates.map((recommendation) => ({
      artistMbid: recommendation.artistMbid,
      artistName: recommendation.artist,
    })),
  );
  const highlights = useMemo(() => {
    const withPhoto = candidates.filter((recommendation) =>
      entdeckenRecommendationHasPhoto(recommendation, imagesByLookupKey),
    );
    return selectEntdeckenHighlightsFromPhotoPool(withPhoto);
  }, [candidates, imagesByLookupKey]);

  return {
    highlights,
    imagesByLookupKey,
    loading,
  };
}

/** Stable lookup signature for preloaded highlight images. */
export function entdeckenHighlightsImageSignature(
  highlights: RecommendationHighlight[],
): string {
  return highlights
    .map((highlight) => {
      const lookupKey = artistImageLookupKey({
        artistMbid: highlight.recommendation.artistMbid,
        artistName: highlight.recommendation.artist,
      });
      return lookupKey;
    })
    .join("|");
}
