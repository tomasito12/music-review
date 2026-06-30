import { useEffect, type ReactElement } from "react";

import { ENTDECKEN_HIGHLIGHTS_SECTION } from "../lib/entdeckenPage";
import { useEntdeckenHighlights } from "../lib/useEntdeckenHighlights";
import type { Recommendation, RecommendationHighlight } from "../types";

import { RecommendationHighlights } from "./RecommendationHighlights";

interface EntdeckenHighlightsSectionProps {
  onHighlightsResolved: (highlights: RecommendationHighlight[]) => void;
  recommendations: Recommendation[];
  showSaveAction?: boolean;
}

/** Photo-gated Entdecken hero built from the top 200 ranked archive rows. */
export function EntdeckenHighlightsSection({
  onHighlightsResolved,
  recommendations,
  showSaveAction = false,
}: EntdeckenHighlightsSectionProps): ReactElement | null {
  const { highlights, imagesByLookupKey, loading } =
    useEntdeckenHighlights(recommendations);

  useEffect(() => {
    if (!loading || highlights.length > 0) {
      onHighlightsResolved(highlights);
    }
  }, [highlights, loading, onHighlightsResolved]);

  if (loading && highlights.length === 0) {
    return (
      <section aria-busy="true" className="highlights-section highlights-section-loading">
        <header className="highlights-section-header">
          <p className="eyebrow">{ENTDECKEN_HIGHLIGHTS_SECTION.eyebrow}</p>
          <h2>{ENTDECKEN_HIGHLIGHTS_SECTION.title}</h2>
          <p className="highlights-section-intro field-hint">
            Fundstücke mit Künstlerfotos werden geladen ...
          </p>
        </header>
      </section>
    );
  }

  if (highlights.length === 0) {
    return null;
  }

  return (
    <RecommendationHighlights
      highlights={highlights}
      imagesByLookupKey={imagesByLookupKey}
      imagesLoading={false}
      sectionCopy={ENTDECKEN_HIGHLIGHTS_SECTION}
      showSaveAction={showSaveAction}
    />
  );
}
