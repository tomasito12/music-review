import type { ReactElement } from "react";

import type { ArtistImageData } from "../lib/artistImageApi";
import { CardExcerpt } from "./CardExcerpt";
import { SaveHeartButton } from "./SaveHeartButton";
import { useFavorites } from "../lib/favoritesContext";
import { recommendationCardMetaParts } from "../lib/recommendationCardMeta";
import {
  recommendationTagStyle,
  visibleRecommendationTags,
} from "../lib/recommendationTagStyles";
import type { RecommendationHighlight } from "../types";
import { formatRankPhotoKicker, shouldShowHighlightCategoryRank } from "../lib/entdeckenPage";

import { ArtistImage } from "./ArtistImage";
import { HighlightAccentPanel } from "./HighlightAccentPanel";

interface HighlightColumnCardBaseProps {
  image: ArtistImageData | null;
  imageLoading: boolean;
  imageOnStart: boolean;
  /** Use a score panel instead of an empty media placeholder when no photo exists. */
  useAccentPanelWithoutPhoto?: boolean;
  showSaveAction: boolean;
}

interface HighlightColumnCardHighlightProps extends HighlightColumnCardBaseProps {
  variant?: "highlight";
  highlight: RecommendationHighlight;
}

interface HighlightColumnCardRankedProps extends HighlightColumnCardBaseProps {
  variant: "ranked";
  recommendation: RecommendationHighlight["recommendation"];
}

type HighlightColumnCardProps =
  | HighlightColumnCardHighlightProps
  | HighlightColumnCardRankedProps;

type HighlightMediaMode = "photo" | "loading" | "accent";

function resolveHighlightMediaMode(
  image: ArtistImageData | null,
  imageLoading: boolean,
  useAccentPanelWithoutPhoto: boolean,
): HighlightMediaMode {
  if (image !== null) {
    return "photo";
  }
  if (useAccentPanelWithoutPhoto) {
    return "accent";
  }
  if (imageLoading) {
    return "loading";
  }
  return "accent";
}

/** One full-width highlight tile with alternating image placement. */
export function HighlightColumnCard(props: HighlightColumnCardProps): ReactElement {
  const {
    image,
    imageLoading,
    imageOnStart,
    useAccentPanelWithoutPhoto = false,
    showSaveAction,
  } = props;

  const isRanked = props.variant === "ranked";
  const recommendation = isRanked ? props.recommendation : props.highlight.recommendation;
  const label = isRanked
    ? formatRankPhotoKicker(recommendation.rank)
    : props.highlight.label;
  const showHighlightCategoryRank = shouldShowHighlightCategoryRank(
    isRanked ? "ranked" : "highlight",
    recommendation.source,
  );
  const description = isRanked ? null : props.highlight.description;
  const isPrimary =
    !isRanked &&
    (props.highlight.label === "Beste Passung" ||
      props.highlight.label === "Beste Gesamtpassung");
  const metaParts = recommendationCardMetaParts(recommendation);
  const tags = visibleRecommendationTags(recommendation.tags);
  const mediaMode = resolveHighlightMediaMode(
    image,
    imageLoading,
    useAccentPanelWithoutPhoto,
  );
  const { isSaved, isToggling, toggleSave } = useFavorites();
  const saved = isSaved(recommendation.reviewId);
  const tileClassName = [
    "highlight-tile",
    imageOnStart ? "highlight-tile-image-start" : "highlight-tile-image-end",
    isPrimary ? "highlight-tile-primary" : "",
  ]
    .filter(Boolean)
    .join(" ");

  return (
    <article className={tileClassName}>
      <div className="highlight-tile-media">
        {mediaMode === "photo" && image !== null ? (
          <ArtistImage artistName={recommendation.artist} image={image} />
        ) : mediaMode === "loading" ? (
          <div
            aria-hidden="true"
            className="highlight-tile-media-panel highlight-tile-media-loading"
          />
        ) : (
          <HighlightAccentPanel
            fitLabel={recommendation.fitLabel}
            fitPercent={recommendation.fitPercent}
            rating={recommendation.rating}
          />
        )}
      </div>

      <div className="highlight-tile-body">

        {showSaveAction && (
          <SaveHeartButton
            className="highlight-save-heart"
            isSaved={saved}
            isToggling={isToggling(recommendation.reviewId)}
            onToggle={() => {
              void toggleSave(recommendation);
            }}
          />
        )}

        <p className={`highlight-tile-kicker${showHighlightCategoryRank ? " highlight-tile-kicker-with-rank" : ""}`}>
          {showHighlightCategoryRank ? (
            <>
              <span>{label}</span>
              <span className="highlight-tile-kicker-rank">
                {formatRankPhotoKicker(recommendation.rank)}
              </span>
            </>
          ) : (
            label
          )}
        </p>
        <h3 className="highlight-tile-title">
          <a href={recommendation.reviewUrl} rel="noreferrer" target="_blank">
            {recommendation.artist} – {recommendation.album}
          </a>
        </h3>
        {description !== null && <p className="highlight-tile-lead">{description}</p>}
        <p className="highlight-tile-meta">{metaParts.join(" · ")}</p>

        {tags.length > 0 && (
          <div
            aria-describedby="recommendation-tag-legend"
            className="tag-row highlight-tile-tags"
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

        <CardExcerpt
          continues={recommendation.excerptContinues}
          text={recommendation.excerpt}
        />
      </div>
    </article>
  );
}
