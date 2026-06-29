import { useMemo, type ReactElement } from "react";

import { artistImageLookupKey } from "../lib/artistImageLookupKey";
import { buildEntdeckenPhotoTileIndices } from "../lib/entdeckenPage";
import { useEntdeckenPhotoSlots } from "../lib/useEntdeckenPhotoSlots";
import type { Recommendation } from "../types";

import { HighlightColumnCard } from "./HighlightColumnCard";
import { RecommendationCard } from "./RecommendationCard";

interface EntdeckenRankingListProps {
  canLoadMore?: boolean;
  excludedArtistLookupKeys?: ReadonlySet<string>;
  loadingMore?: boolean;
  onLoadMore?: () => void;
  recommendations: Recommendation[];
  showSaveAction?: boolean;
}

/** Entdecken ranking list with sparse photo tiles between dense cards. */
export function EntdeckenRankingList({
  canLoadMore = false,
  excludedArtistLookupKeys = new Set(),
  loadingMore = false,
  onLoadMore,
  recommendations,
  showSaveAction = false,
}: EntdeckenRankingListProps): ReactElement {
  const { imagesByLookupKey, loadingPhotoRanks, photoRanks } =
    useEntdeckenPhotoSlots(recommendations, excludedArtistLookupKeys);
  const photoTileIndices = useMemo(
    () => buildEntdeckenPhotoTileIndices(recommendations, photoRanks),
    [photoRanks, recommendations],
  );

  function renderRecommendation(
    recommendation: Recommendation,
    keySuffix: string,
  ): ReactElement {
    const lookupKey = artistImageLookupKey({
      artistMbid: recommendation.artistMbid,
      artistName: recommendation.artist,
    });
    const isPhotoRank = photoRanks.has(recommendation.rank);
    const isLoadingPhoto = loadingPhotoRanks.has(recommendation.rank);

    if (isPhotoRank || isLoadingPhoto) {
      const photoTileIndex = photoTileIndices.get(recommendation.rank) ?? 0;
      return (
        <HighlightColumnCard
          image={isPhotoRank && lookupKey ? imagesByLookupKey.get(lookupKey) ?? null : null}
          imageLoading={isLoadingPhoto}
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
    <section aria-labelledby="ranking-heading" className="ranking-section ranking-section-after-prelude">
      <div className="ranking-heading">
        <h2 id="ranking-heading">Alle Empfehlungen</h2>
        <p>Sortiert nach Gesamtscore (Passung, Wertung und Stilbreite).</p>
      </div>
      <div className="recommendation-list">
        {recommendations.map((recommendation) =>
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
  );
}
