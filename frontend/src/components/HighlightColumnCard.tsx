import type { ReactElement } from "react";

import type { ArtistImageData } from "../lib/artistImageApi";
import { CardExcerpt } from "./CardExcerpt";
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
  if (imageLoading) {
    return (
      <div
        aria-hidden="true"
        className="highlight-tile-media-panel highlight-tile-media-loading"
      />
    );
  }
  return (
    <div
      aria-hidden="true"
      className="highlight-tile-media-panel highlight-tile-media-fallback"
    />
  );
}

/** One full-width highlight tile with alternating image placement. */
export function HighlightColumnCard(props: HighlightColumnCardProps): ReactElement {
  const { image, imageLoading, imageOnStart, showSaveAction } = props;
  const recommendation =
    props.variant === "ranked" ? props.recommendation : props.highlight.recommendation;
  const label =
    props.variant === "ranked"
      ? formatRankPhotoKicker(recommendation.rank)
      : props.highlight.label;
  const description = props.variant === "ranked" ? null : props.highlight.description;
  const isPrimary =
    props.variant !== "ranked" && props.highlight.label === "Beste Passung";
  const metaParts = recommendationCardMetaParts(recommendation);
  const tags = visibleRecommendationTags(recommendation.tags);

  return (
    <article
      className={`highlight-tile${
        imageOnStart ? " highlight-tile-image-start" : " highlight-tile-image-end"
      }${isPrimary ? " highlight-tile-primary" : ""}`}
    >
      <div className="highlight-tile-media">
        <HighlightTileMedia
          artistName={recommendation.artist}
          image={image}
          imageLoading={imageLoading}
        />
      </div>

      <div className="highlight-tile-body">
        {showSaveAction && (
          <button
            aria-label="Vormerken"
            className="highlight-save-heart"
            disabled
            title="Vormerken kommt in einer späteren Ausbaustufe."
            type="button"
          >
            <svg aria-hidden="true" className="card-save-heart-icon" viewBox="0 0 24 24">
              <path d="M12 20.25s-6.9-4.35-9.33-7.58C.86 10.03 1.1 6.88 3.45 5.1 5.8 3.32 8.9 4.04 12 6.7c3.1-2.66 6.2-3.38 8.55-1.6 2.35 1.78 2.59 4.93.78 7.57C18.9 15.9 12 20.25 12 20.25z" />
            </svg>
          </button>
        )}

        <p className="highlight-tile-kicker">{label}</p>
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

        <CardExcerpt text={recommendation.excerpt} />
      </div>
    </article>
  );
}
