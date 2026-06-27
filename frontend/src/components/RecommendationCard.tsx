import type { ReactElement } from "react";

import type { Recommendation } from "../types";

import { CardExcerpt } from "./CardExcerpt";
import { recommendationCardMetaParts } from "../lib/recommendationCardMeta";
import {
  recommendationTagStyle,
  visibleRecommendationTags,
} from "../lib/recommendationTagStyles";

interface RecommendationCardProps {
  recommendation: Recommendation;
  showSaveAction?: boolean;
  variant?: "regular" | "feature";
}

export function RecommendationCard({
  recommendation,
  showSaveAction = false,
  variant = "regular",
}: RecommendationCardProps): ReactElement {
  const metaParts = recommendationCardMetaParts(recommendation);
  const tags = visibleRecommendationTags(recommendation.tags);
  return (
    <article
      className={`recommendation-card recommendation-card-${variant}${
        showSaveAction ? " recommendation-card-with-save" : ""
      }`}
    >
      {showSaveAction && (
        <button
          aria-label="Vormerken"
          className="card-save-heart"
          disabled
          title="Vormerken kommt in einer späteren Ausbaustufe."
          type="button"
        >
          <svg aria-hidden="true" className="card-save-heart-icon" viewBox="0 0 24 24">
            <path d="M12 20.25s-6.9-4.35-9.33-7.58C.86 10.03 1.1 6.88 3.45 5.1 5.8 3.32 8.9 4.04 12 6.7c3.1-2.66 6.2-3.38 8.55-1.6 2.35 1.78 2.59 4.93.78 7.57C18.9 15.9 12 20.25 12 20.25z" />
          </svg>
        </button>
      )}
      <div className="rank" aria-label={`Listenposition ${recommendation.rank}`}>
        <span>{recommendation.rank.toString().padStart(2, "0")}</span>
      </div>
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
        <CardExcerpt text={recommendation.excerpt} />
      </div>
    </article>
  );
}
