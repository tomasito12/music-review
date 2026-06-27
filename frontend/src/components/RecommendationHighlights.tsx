import type { ReactElement } from "react";

import type { RecommendationHighlight } from "../types";

import { RecommendationCard } from "./RecommendationCard";

interface RecommendationHighlightsProps {
  highlights: RecommendationHighlight[];
  showSaveAction?: boolean;
}

/** Shows a small editorial selection before the complete ranking. */
export function RecommendationHighlights({
  highlights,
  showSaveAction = false,
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
            <RecommendationCard
              recommendation={highlight.recommendation}
              showSaveAction={showSaveAction}
              variant="feature"
            />
          </article>
        ))}
      </div>
    </div>
  );
}
