import type { ReactElement } from "react";

import { artistImageLookupKey } from "../lib/artistImageLookupKey";
import { useArtistImagesBatch } from "../lib/useArtistImagesBatch";
import type { RecommendationHighlight } from "../types";

import { HighlightColumnCard } from "./HighlightColumnCard";

interface RecommendationHighlightsProps {
  highlights: RecommendationHighlight[];
  showSaveAction?: boolean;
}

/** Editorial highlight section with full-width alternating tiles. */
export function RecommendationHighlights({
  highlights,
  showSaveAction = false,
}: RecommendationHighlightsProps): ReactElement {
  const { imagesByLookupKey, loading } = useArtistImagesBatch(
    highlights.map((highlight) => ({
      artistMbid: highlight.recommendation.artistMbid,
      artistName: highlight.recommendation.artist,
    })),
  );

  return (
    <section aria-labelledby="highlights-heading" className="highlights-section">
      <header className="highlights-section-header">
        <p className="eyebrow">Persönlich für dich</p>
        <h2 id="highlights-heading">Deine Highlights</h2>
        <p className="highlights-section-intro">
          Drei Fundstücke aus dem aktuellen Update – zum Reinhören, Mitnehmen und
          vielleicht sogar als neuer Liebling entdecken.
        </p>
      </header>

      <div className="highlights-stack">
        {highlights.map((highlight, index) => {
          const lookupKey = artistImageLookupKey({
            artistMbid: highlight.recommendation.artistMbid,
            artistName: highlight.recommendation.artist,
          });
          return (
            <HighlightColumnCard
              highlight={highlight}
              image={
                lookupKey ? imagesByLookupKey.get(lookupKey) ?? null : null
              }
              imageLoading={loading && Boolean(lookupKey)}
              imageOnStart={index % 2 === 0}
              key={highlight.label}
              showSaveAction={showSaveAction}
            />
          );
        })}
      </div>
    </section>
  );
}
