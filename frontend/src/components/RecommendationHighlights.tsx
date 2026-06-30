import type { ReactElement } from "react";

import type { ArtistImageData } from "../lib/artistImageApi";
import { artistImageLookupKey } from "../lib/artistImageLookupKey";
import { useArtistImagesBatch } from "../lib/useArtistImagesBatch";
import type { RecommendationHighlight } from "../types";

import { HighlightColumnCard } from "./HighlightColumnCard";

export interface HighlightsSectionCopy {
  eyebrow: string;
  intro: string;
  title: string;
}

const DEFAULT_SECTION_COPY: HighlightsSectionCopy = {
  eyebrow: "Persönlich für dich",
  title: "Deine Highlights",
  intro:
    "Drei Fundstücke aus dem aktuellen Update – zum Reinhören, Mitnehmen und vielleicht sogar als neuer Liebling entdecken.",
};

interface RecommendationHighlightsProps {
  dataVisualHighlights?: "pending" | "ready";
  highlights: RecommendationHighlight[];
  imagesByLookupKey?: Map<string, ArtistImageData | null>;
  imagesLoading?: boolean;
  sectionCopy?: HighlightsSectionCopy;
  showSaveAction?: boolean;
}

/** Editorial highlight section with full-width alternating tiles. */
export function RecommendationHighlights({
  dataVisualHighlights,
  highlights,
  imagesByLookupKey: preloadedImages,
  imagesLoading: preloadedLoading,
  sectionCopy = DEFAULT_SECTION_COPY,
  showSaveAction = false,
}: RecommendationHighlightsProps): ReactElement {
  const batch = useArtistImagesBatch(
    preloadedImages === undefined
      ? highlights.map((highlight) => ({
          artistMbid: highlight.recommendation.artistMbid,
          artistName: highlight.recommendation.artist,
        }))
      : [],
  );
  const imagesByLookupKey = preloadedImages ?? batch.imagesByLookupKey;

  return (
    <section
      aria-labelledby="highlights-heading"
      className="highlights-section"
      data-visual-highlights={dataVisualHighlights}
    >
      <header className="highlights-section-header">
        <p className="eyebrow">{sectionCopy.eyebrow}</p>
        <h2 id="highlights-heading">{sectionCopy.title}</h2>
        <p className="highlights-section-intro">{sectionCopy.intro}</p>
      </header>

      <div className="highlights-stack">
        {highlights.map((highlight, index) => {
          const lookupKey = artistImageLookupKey({
            artistMbid: highlight.recommendation.artistMbid,
            artistName: highlight.recommendation.artist,
          });
          const imageResolved = lookupKey ? imagesByLookupKey.has(lookupKey) : true;
          return (
            <HighlightColumnCard
              highlight={highlight}
              image={
                lookupKey ? imagesByLookupKey.get(lookupKey) ?? null : null
              }
              imageLoading={Boolean(lookupKey) && !imageResolved}
              imageOnStart={index % 2 === 0}
              key={highlight.label}
              useAccentPanelWithoutPhoto
              showSaveAction={showSaveAction}
            />
          );
        })}
      </div>
    </section>
  );
}
