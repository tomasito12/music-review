import type { ReactElement, ReactNode } from "react";

import type { RecommendationSource } from "../types";

import { RecommendationTagLegend } from "./RecommendationTagLegend";

const PRELUDE_COPY: Record<RecommendationSource, string> = {
  aktuell:
    "Passe Zeitraum, Presets und Gewichtung an — die Highlights oben bleiben, die Liste darunter aktualisiert sich.",
  entdecken:
    "Sortierung und Filter wirken auf das gesamte Archiv. Die vier Fundstücke oben bleiben als Einstieg.",
};

interface ResultsListPreludeProps {
  filterRegion: ReactNode;
  source: RecommendationSource;
}

/** Framed filter station between editorial highlights and the dense ranking list. */
export function ResultsListPrelude({
  filterRegion,
  source,
}: ResultsListPreludeProps): ReactElement {
  return (
    <section aria-labelledby="list-tuning-heading" className="results-list-prelude">
      <header className="results-list-prelude-header">
        <p className="eyebrow">Feintuning</p>
        <h2 id="list-tuning-heading">Liste verfeinern</h2>
        <p>{PRELUDE_COPY[source]}</p>
      </header>
      {filterRegion}
      <RecommendationTagLegend />
    </section>
  );
}
