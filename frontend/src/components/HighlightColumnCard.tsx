import type { ReactElement } from "react";

import { artistInitials } from "../lib/artistInitials";
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
import { formatRankPhotoKicker } from "../lib/entdeckenPage";

import { ArtistImage } from "./ArtistImage";

interface HighlightColumnCardBaseProps {
  image: ArtistImageData | null;
  imageLoading: boolean;
  imageOnStart: boolean;
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

type HighlightMediaMode = "photo" | "loading" | "textOnly";

function resolveHighlightMediaMode(
  image: ArtistImageData | null,
  imageLoading: boolean,
): HighlightMediaMode {
  if (image !== null) {
    return "photo";
  }
  if (imageLoading) {
    return "loading";
  }
  return "textOnly";
}

function HighlightTileMedia({
  artistName,
  image,
  imageLoading,
}: {
  artistName: string;
  image: ArtistImageData | null;
  imageLoading: boolean;
}): ReactElement {
  if (image !== null) {
    return <ArtistImage artistName={artistName} image={image} />;
  }
  return (
    <div
      aria-hidden="true"
      className={`highlight-tile-media-panel${
        imageLoading ? " highlight-tile-media-loading" : " highlight-tile-media-fallback"
      }`}
    />
  );
}

/** One full-width highlight tile with alternating image placement. */
export function HighlightColumnCard(props: HighlightColumnCardProps): ReactElement {
  const { image, imageLoading, imageOnStart, showSaveAction } = props;
  const variant = props.variant ?? "highlight";
  const recommendation =
    variant === "ranked" ? props.recommendation : props.highlight.recommendation;
  const label =
    variant === "ranked"
      ? formatRankPhotoKicker(recommendation.rank)
      : props.highlight.label;
  const showEntdeckenArchiveRank =
    variant === "highlight" && recommendation.source === "entdecken";
  const description = variant === "ranked" ? null : props.highlight.description;
  const isPrimary =
    variant !== "ranked" &&
    (props.highlight.label === "Beste Passung" ||
      props.highlight.label === "Beste Gesamtpassung");
  const metaParts = recommendationCardMetaParts(recommendation);
  const tags = visibleRecommendationTags(recommendation.tags);
  const mediaMode = resolveHighlightMediaMode(image, imageLoading);
  const { isSaved, isToggling, toggleSave } = useFavorites();
  const saved = isSaved(recommendation.reviewId);
  const tileClassName = [
    "highlight-tile",
    mediaMode === "textOnly"
      ? "highlight-tile-text-only"
      : imageOnStart
        ? "highlight-tile-image-start"
        : "highlight-tile-image-end",
    isPrimary ? "highlight-tile-primary" : "",
  ]
    .filter(Boolean)
    .join(" ");

  return (
    <article className={tileClassName}>
      {mediaMode !== "textOnly" && (
        <div className="highlight-tile-media">
          <HighlightTileMedia
            artistName={recommendation.artist}
            image={image}
            imageLoading={mediaMode === "loading"}
          />
        </div>
      )}

      <div className="highlight-tile-body">
        {mediaMode === "textOnly" && (
          <p aria-hidden="true" className="highlight-tile-initials">
            {artistInitials(recommendation.artist)}
          </p>
        )}

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

        <p className={`highlight-tile-kicker${showEntdeckenArchiveRank ? " highlight-tile-kicker-with-rank" : ""}`}>
          {showEntdeckenArchiveRank ? (
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
