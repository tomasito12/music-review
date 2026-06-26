import type { ReactElement } from "react";

import type { Recommendation, RecommendationSource } from "../types";

import { RecommendationCard } from "./RecommendationCard";

interface RecommendationListProps {
  title: string;
  message: string;
  source: RecommendationSource;
  recommendations: Recommendation[];
  onCreatePlaylist: (source: RecommendationSource) => void;
}

export function RecommendationList({
  title,
  message,
  source,
  recommendations,
  onCreatePlaylist,
}: RecommendationListProps): ReactElement {
  return (
    <section className="results-page">
      <div className="results-header">
        <div>
          <p className="eyebrow">{source === "aktuell" ? "Neue Rezensionen" : "Archiv"}</p>
          <h1>{title}</h1>
          <p>{message}</p>
        </div>
        <button
          className="primary-button"
          onClick={() => onCreatePlaylist(source)}
          type="button"
        >
          Playlist erzeugen
        </button>
      </div>

      {source === "aktuell" && (
        <div className="range-control" aria-label="Update-Zeitraum">
          <label>
            Zeitraum
            <select defaultValue="4">
              <option value="1">Letzte Update-Runde</option>
              <option value="4">Letzte 4 Update-Runden</option>
              <option value="8">Letzte 8 Update-Runden</option>
            </select>
          </label>
          <p>
            Später basiert diese Auswahl auf gespeicherten Update-Daten. In der
            Shell zeigt sie den geplanten Bedienfluss.
          </p>
        </div>
      )}

      <div className="filter-summary" aria-label="Aktuelle Filter">
        <span>Ausgewogen</span>
        <span>Stilpassung sichtbar</span>
        <span>Temporär anpassbar</span>
        <button type="button">Filter anpassen</button>
      </div>

      <div className="recommendation-list">
        {recommendations.map((item) => (
          <RecommendationCard key={`${item.source}-${item.rank}`} recommendation={item} />
        ))}
      </div>
    </section>
  );
}
