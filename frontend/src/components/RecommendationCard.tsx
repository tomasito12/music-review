import type { ReactElement } from "react";

import type { Recommendation } from "../types";

import { recommendationCardMetaParts } from "../lib/recommendationCardMeta";

interface RecommendationCardProps {
  recommendation: Recommendation;
}

export function RecommendationCard({
  recommendation,
}: RecommendationCardProps): ReactElement {
  const metaParts = recommendationCardMetaParts(recommendation);

  return (
    <article className="recommendation-card">
      <div className="rank" aria-label={`Rang ${recommendation.rank}`}>
        {recommendation.rank.toString().padStart(2, "0")}
      </div>
      <div className="card-main">
        <h2>
          <a href={recommendation.reviewUrl} rel="noreferrer" target="_blank">
            {recommendation.artist} - {recommendation.album}
          </a>
        </h2>
        <p className="card-meta">{metaParts.join(" · ")}</p>
        <div className="card-secondary">
          <span
            className="card-fit-badge"
            title={`${recommendation.fitPercent}% Passung zu deinem Profil`}
          >
            {recommendation.fitLabel}
          </span>
          <span
            aria-label={`Gesamtscore ${recommendation.score.toFixed(2)}`}
            className="card-score"
          >
            Score {recommendation.score.toFixed(2)}
          </span>
        </div>
        <p className="excerpt">{recommendation.excerpt}</p>
        <div className="tag-row" aria-label="Passende Stilrichtungen">
          {recommendation.tags.map((tag) => (
            <span
              className={`tag tag-${tag.strength}${
                tag.matchesProfile ? " tag-match" : " tag-neutral"
              }`}
              key={tag.label}
              title={
                tag.matchesProfile
                  ? "Passt zu deinem Musikprofil"
                  : "Stilzuordnung dieses Albums"
              }
            >
              {tag.label}
            </span>
          ))}
        </div>
      </div>
    </article>
  );
}
