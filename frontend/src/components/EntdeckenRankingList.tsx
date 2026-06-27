import { useMemo, type ReactElement, type ReactNode } from "react";

import { artistImageLookupKey } from "../lib/artistImageLookupKey";
import {
  buildEntdeckenPhotoTileIndices,
  entdeckenPhotoLookupRecommendations,
  entdeckenRecommendationHasPhoto,
  resolveEntdeckenPhotoRanks,
} from "../lib/entdeckenPage";
import { useArtistImagesBatch } from "../lib/useArtistImagesBatch";
import type { Recommendation } from "../types";

import { HighlightColumnCard } from "./HighlightColumnCard";
import { RecommendationCard } from "./RecommendationCard";

interface EntdeckenRankingListProps {
  canLoadMore?: boolean;
  filterRegion: ReactNode;
  loadingMore?: boolean;
  onLoadMore?: () => void;
  recommendations: Recommendation[];
  showSaveAction?: boolean;
}

/** Entdecken ranking list with rank 1 first, filters second, and sparse photo tiles. */
export function EntdeckenRankingList({
  canLoadMore = false,
  filterRegion,
  loadingMore = false,
  onLoadMore,
  recommendations,
  showSaveAction = false,
}: EntdeckenRankingListProps): ReactElement {
  const photoLookupRecommendations = useMemo(
    () => entdeckenPhotoLookupRecommendations(recommendations),
    [recommendations],
  );
  const { imagesByLookupKey, loading: imagesLoading } = useArtistImagesBatch(
    photoLookupRecommendations.map((recommendation) => ({
      artistMbid: recommendation.artistMbid,
      artistName: recommendation.artist,
    })),
  );
  const photoRanks = useMemo(
    () =>
      imagesLoading
        ? new Set<number>()
        : resolveEntdeckenPhotoRanks(recommendations, (recommendation) =>
            entdeckenRecommendationHasPhoto(recommendation, imagesByLookupKey),
          ),
    [imagesByLookupKey, imagesLoading, recommendations],
  );
  const photoTileIndices = useMemo(
    () => buildEntdeckenPhotoTileIndices(recommendations, photoRanks),
    [photoRanks, recommendations],
  );
  const leadRecommendation = recommendations.find((recommendation) => recommendation.rank === 1);
  const remainingRecommendations = recommendations.filter(
    (recommendation) => recommendation.rank !== 1,
  );

  function renderRecommendation(
    recommendation: Recommendation,
    keySuffix: string,
  ): ReactElement {
    const photoTileIndex = photoTileIndices.get(recommendation.rank);
    if (photoTileIndex !== undefined) {
      const lookupKey = artistImageLookupKey({
        artistMbid: recommendation.artistMbid,
        artistName: recommendation.artist,
      });
      return (
        <HighlightColumnCard
          image={lookupKey ? imagesByLookupKey.get(lookupKey) ?? null : null}
          imageLoading={imagesLoading && lookupKey.length > 0}
          imageOnStart={photoTileIndex % 2 === 0}
          key={`${recommendation.source}-${recommendation.rank}-${keySuffix}`}
          recommendation={recommendation}
          showSaveAction={showSaveAction}
          variant="ranked"
        />
      );
    }

    return (
      <RecommendationCard
        key={`${recommendation.source}-${recommendation.rank}-${keySuffix}`}
        recommendation={recommendation}
        showSaveAction={showSaveAction}
      />
    );
  }

  return (
    <>
      {leadRecommendation !== undefined && (
        <div className="entdecken-lead-entry">
          {renderRecommendation(leadRecommendation, "lead")}
        </div>
      )}

      <div className="entdecken-list-prelude">{filterRegion}</div>

      <section aria-labelledby="ranking-heading" className="ranking-section">
        <div className="ranking-heading">
          <h2 id="ranking-heading">Alle Empfehlungen</h2>
          <p>Sortiert nach der Passung zu deinem Musikprofil.</p>
        </div>
        <div className="recommendation-list">
          {remainingRecommendations.map((recommendation) =>
            renderRecommendation(recommendation, "list"),
          )}
        </div>
        {canLoadMore && onLoadMore !== undefined && (
          <div className="results-load-more">
            <button
              className="secondary-button"
              disabled={loadingMore}
              onClick={onLoadMore}
              type="button"
            >
              {loadingMore ? "Weitere Alben werden geladen ..." : "Weitere Alben laden"}
            </button>
          </div>
        )}
      </section>
    </>
  );
}
