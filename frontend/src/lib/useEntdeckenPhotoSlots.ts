import { useEffect, useMemo, useState } from "react";

import { ApiClient } from "./apiClient";
import { loadArtistImagesBatch, type ArtistImageData } from "./artistImageApi";
import { artistImageLookupKey } from "./artistImageLookupKey";
import {
  entdeckenPhotoSlotGroups,
  entdeckenRecommendationHasPhoto,
} from "./entdeckenPage";
import type { Recommendation } from "../types";

export interface UseEntdeckenPhotoSlotsResult {
  imagesByLookupKey: Map<string, ArtistImageData | null>;
  loadingPhotoRanks: Set<number>;
  photoRanks: Set<number>;
}

function recommendationLookupKey(recommendation: Recommendation): string {
  return artistImageLookupKey({
    artistMbid: recommendation.artistMbid,
    artistName: recommendation.artist,
  });
}

/** Resolve Entdecken photo slots one group at a time so the first tiles appear quickly. */
export function useEntdeckenPhotoSlots(
  recommendations: Recommendation[],
): UseEntdeckenPhotoSlotsResult {
  const [imagesByLookupKey, setImagesByLookupKey] = useState<
    Map<string, ArtistImageData | null>
  >(new Map());
  const [loadingPhotoRanks, setLoadingPhotoRanks] = useState<Set<number>>(new Set());
  const [photoRanks, setPhotoRanks] = useState<Set<number>>(new Set());

  const recommendationSignature = useMemo(
    () =>
      recommendations
        .map(
          (recommendation) =>
            `${recommendation.rank}:${recommendation.artist}:${recommendation.artistMbid ?? ""}`,
        )
        .join("|"),
    [recommendations],
  );

  useEffect(() => {
    if (recommendations.length === 0) {
      setImagesByLookupKey(new Map());
      setLoadingPhotoRanks(new Set());
      setPhotoRanks(new Set());
      return;
    }

    let active = true;
    const rankByNumber = new Map(
      recommendations.map((recommendation) => [recommendation.rank, recommendation]),
    );
    const maxRank = Math.max(...recommendations.map((recommendation) => recommendation.rank));
    const slotGroups = entdeckenPhotoSlotGroups(maxRank);
    const resolvedImages = new Map<string, ArtistImageData | null>();
    const resolvedPhotoRanks = new Set<number>();
    const claimedRanks = new Set<number>();

    async function resolvePhotoSlots(): Promise<void> {
      const client = new ApiClient();

      for (const candidates of slotGroups) {
        if (!active) {
          return;
        }

        const availableCandidates = candidates.filter((rank) => {
          if (claimedRanks.has(rank)) {
            return false;
          }
          return rankByNumber.has(rank);
        });
        if (availableCandidates.length === 0) {
          continue;
        }

        const lookupRecommendations = availableCandidates
          .map((rank) => rankByNumber.get(rank))
          .filter((recommendation): recommendation is Recommendation => recommendation !== undefined)
          .filter((recommendation) => recommendationLookupKey(recommendation).length > 0);

        const pendingLookupKeys = lookupRecommendations
          .map((recommendation) => recommendationLookupKey(recommendation))
          .filter((lookupKey) => !resolvedImages.has(lookupKey));

        const primaryCandidate = availableCandidates[0];
        if (primaryCandidate !== undefined && pendingLookupKeys.length > 0) {
          setLoadingPhotoRanks(new Set([primaryCandidate]));
        }

        if (lookupRecommendations.length > 0 && pendingLookupKeys.length > 0) {
          try {
            const batchResults = await loadArtistImagesBatch(
              client,
              lookupRecommendations.map((recommendation) => ({
                artistMbid: recommendation.artistMbid,
                artistName: recommendation.artist,
              })),
            );
            if (!active) {
              return;
            }
            for (const [lookupKey, image] of batchResults) {
              resolvedImages.set(lookupKey, image);
            }
            setImagesByLookupKey(new Map(resolvedImages));
          } catch {
            if (!active) {
              return;
            }
          }
        }

        const selectedRank = availableCandidates.find((rank) => {
          const recommendation = rankByNumber.get(rank);
          if (recommendation === undefined) {
            return false;
          }
          return entdeckenRecommendationHasPhoto(recommendation, resolvedImages);
        });

        if (selectedRank !== undefined) {
          resolvedPhotoRanks.add(selectedRank);
          claimedRanks.add(selectedRank);
          setPhotoRanks(new Set(resolvedPhotoRanks));
        }

        if (!active) {
          return;
        }
        setLoadingPhotoRanks(new Set());
      }
    }

    void resolvePhotoSlots();

    return () => {
      active = false;
    };
  }, [recommendationSignature, recommendations]);

  return {
    imagesByLookupKey,
    loadingPhotoRanks,
    photoRanks,
  };
}
