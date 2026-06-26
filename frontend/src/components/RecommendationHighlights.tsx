import type { ReactElement } from "react";

import type { RecommendationHighlight } from "../types";

interface RecommendationHighlightsProps {
  highlights: RecommendationHighlight[];
}

/** Shows a small editorial selection before the complete ranking. */
export function RecommendationHighlights({
  highlights,
}: RecommendationHighlightsProps): ReactElement {
  return (
    <div className="recommendation-highlights">
      <div className="highlight-grid">
        {highlights.map((highlight) => (
          <article
            className={`highlight-card${
              highlight.label === "Beste Passung" ? " highlight-card-primary" : ""
            }`}
            key={highlight.label}
          >
            <p className="highlight-label">{highlight.label}</p>
            <h3>
              <a
                href={highlight.recommendation.reviewUrl}
                rel="noreferrer"
                target="_blank"
              >
                {highlight.recommendation.artist} - {highlight.recommendation.album}
              </a>
            </h3>
            <p>{highlight.description}</p>
            <div className="highlight-meta">
              <span>{highlight.recommendation.rating}/10 bei plattentests.de</span>
              <span>Score {highlight.recommendation.score.toFixed(2)}</span>
            </div>
          </article>
        ))}
      </div>
    </div>
  );
}
