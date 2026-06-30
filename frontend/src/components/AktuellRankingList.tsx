import { useEffect, type ReactElement } from "react";

import { artistImageLookupKey } from "../lib/artistImageLookupKey";
import { limitRecommendationsForVisualTest } from "../lib/visualTestListLimit";
import { useArtistImagesBatch } from "../lib/useArtistImagesBatch";
import type { Recommendation } from "../types";

import { RecommendationCard } from "./RecommendationCard";

interface AktuellRankingListProps {
  canLoadMore?: boolean;
  loadingMore?: boolean;
  onLoadMore?: () => void;
  onRankingReady?: () => void;
  recommendations: Recommendation[];
  showSaveAction?: boolean;
}

/** Neuheiten ranking list with optional artist thumbnails when images are available. */
export function AktuellRankingList({
  canLoadMore = false,
  loadingMore = false,
  onLoadMore,
  onRankingReady,
  recommendations,
  showSaveAction = false,
}: AktuellRankingListProps): ReactElement {
  const visibleRecommendations = limitRecommendationsForVisualTest(recommendations);
  const { imagesByLookupKey, imagesSettled } = useArtistImagesBatch(
    visibleRecommendations.map((recommendation) => ({
      artistMbid: recommendation.artistMbid,
      artistName: recommendation.artist,
    })),
  );

  useEffect(() => {
    if (imagesSettled) {
      onRankingReady?.();
    }
  }, [imagesSettled, onRankingReady]);

  return (
    <section
      aria-labelledby="ranking-heading"
      className="ranking-section ranking-section-after-prelude"
      data-visual-images={imagesSettled ? "ready" : "pending"}
    >
      <div className="ranking-heading">
        <h2 id="ranking-heading">Weitere neue Rezensionen</h2>
        <p>Dichter sortiert, damit du den Update-Schwung schnell scannen kannst.</p>
      </div>
      <div className="recommendation-list">
        {visibleRecommendations.map((recommendation) => {
          const lookupKey = artistImageLookupKey({
            artistMbid: recommendation.artistMbid,
            artistName: recommendation.artist,
          });
          const artistImage =
            lookupKey.length > 0
              ? imagesByLookupKey.get(lookupKey) ?? null
              : null;
          return (
            <RecommendationCard
              artistImage={artistImage}
              key={`${recommendation.source}-${recommendation.rank}`}
              recommendation={recommendation}
              showSaveAction={showSaveAction}
            />
          );
        })}
      </div>
      {canLoadMore && onLoadMore !== undefined && recommendations.length > visibleRecommendations.length && (
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
