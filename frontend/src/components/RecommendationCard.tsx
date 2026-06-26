import type { ReactElement } from "react";

import type { Recommendation } from "../types";

interface RecommendationCardProps {
  recommendation: Recommendation;
}

export function RecommendationCard({
  recommendation,
}: RecommendationCardProps): ReactElement {
  return (
    <article className="recommendation-card">
      <div className="rank" aria-label={`Rang ${recommendation.rank}`}>
        {recommendation.rank.toString().padStart(2, "0")}
      </div>
      <div className="card-main">
        <div className="card-kicker">
          <span>{recommendation.year}</span>
          <span>{recommendation.rating}/10 bei plattentests.de</span>
          <span>Score {recommendation.score.toFixed(2)}</span>
          {recommendation.recordLabel !== undefined && (
            <span>Label: {recommendation.recordLabel}</span>
          )}
          <span className="fit-label" title={`${recommendation.fitPercent}% Fit`}>
            {recommendation.fitLabel}
          </span>
        </div>
        <h2>
          <a href={recommendation.reviewUrl} rel="noreferrer" target="_blank">
            {recommendation.artist} - {recommendation.album}
          </a>
        </h2>
        <p className="excerpt">{recommendation.excerpt}</p>
        <div className="tag-row" aria-label="Passende Stilrichtungen">
          {recommendation.tags.map((tag) => (
            <span
              className={`tag tag-${tag.strength}${
                tag.matchesProfile ? " tag-match" : ""
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
