import { useEffect, useState, type ReactElement } from "react";

import type { ArtistImageData } from "../lib/artistImageApi";
import type { Recommendation } from "../types";

import { ArtistListThumbnail } from "./ArtistListThumbnail";
import { CardExcerpt } from "./CardExcerpt";
import { SaveHeartButton } from "./SaveHeartButton";
import { useFavorites } from "../lib/favoritesContext";
import { recommendationCardMetaParts } from "../lib/recommendationCardMeta";
import {
  recommendationTagStyle,
  visibleRecommendationTags,
} from "../lib/recommendationTagStyles";

interface RecommendationCardProps {
  artistImage?: ArtistImageData | null;
  recommendation: Recommendation;
  showSaveAction?: boolean;
  variant?: "regular" | "feature";
}

export function RecommendationCard({
  artistImage = null,
  recommendation,
  showSaveAction = false,
  variant = "regular",
}: RecommendationCardProps): ReactElement {
  const metaParts = recommendationCardMetaParts(recommendation);
  const tags = visibleRecommendationTags(recommendation.tags);
  const { isSaved, isToggling, toggleSave } = useFavorites();
  const saved = isSaved(recommendation.reviewId);
  const [thumbnailVisible, setThumbnailVisible] = useState(artistImage !== null);

  useEffect(() => {
    setThumbnailVisible(artistImage !== null);
  }, [artistImage]);

  const showThumbnail = artistImage !== null && thumbnailVisible;
  return (
    <article
      className={`recommendation-card recommendation-card-${variant}${
        showSaveAction ? " recommendation-card-with-save" : ""
      }${showThumbnail ? " recommendation-card-with-thumbnail" : ""}`}
    >
      {showSaveAction && (
        <SaveHeartButton
          isSaved={saved}
          isToggling={isToggling(recommendation.reviewId)}
          onToggle={() => {
            void toggleSave(recommendation);
          }}
        />
      )}
      <div className="rank" aria-label={`Listenposition ${recommendation.rank}`}>
        <span>{recommendation.rank.toString().padStart(2, "0")}</span>
      </div>
      {showThumbnail && artistImage !== null && (
        <ArtistListThumbnail
          artistName={recommendation.artist}
          image={artistImage}
          onFailed={() => {
            setThumbnailVisible(false);
          }}
        />
      )}
      <div className="card-main">
        <h2>
          <a href={recommendation.reviewUrl} rel="noreferrer" target="_blank">
            {recommendation.artist} - {recommendation.album}
          </a>
        </h2>
        <p className="card-meta">{metaParts.join(" · ")}</p>
        {tags.length > 0 && (
          <div
            aria-describedby="recommendation-tag-legend"
            className="tag-row"
            aria-label="Stilrichtungen"
          >
            {tags.map((tag) => (
              <span
                className={`tag${tag.matchesProfile ? " tag-match" : ""}`}
                key={`${tag.label}-${tag.affinity}`}
                style={recommendationTagStyle(tag)}
                title={
                  tag.matchesProfile
                    ? `${tag.label}: passt zu deinem Musikprofil`
                    : `${tag.label}: Stilnähe zum Album`
                }
              >
                {tag.label}
              </span>
            ))}
          </div>
        )}
        <CardExcerpt continues={recommendation.excerptContinues} text={recommendation.excerpt} />
      </div>
    </article>
  );
}
