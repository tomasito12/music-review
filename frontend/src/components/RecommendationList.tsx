import type { ReactElement } from "react";

import type {
  Recommendation,
  RecommendationHighlight,
  RecommendationSource,
  UpdateSummary,
} from "../types";
import type { TasteCommunityOption, TasteFilterSettings, TastePreset } from "../lib/plattenradarApi";
import type { ProfileSetupResult } from "../lib/profileSessionStorage";

import { RecommendationCard } from "./RecommendationCard";
import { RecommendationHighlights } from "./RecommendationHighlights";
import { ResultsFilterPanel } from "./ResultsFilterPanel";

interface RecommendationListProps {
  title: string;
  message: string;
  source: RecommendationSource;
  recommendations: Recommendation[];
  highlights?: RecommendationHighlight[];
  updateSummary?: UpdateSummary;
  filterSummary?: string[];
  canLoadMore?: boolean;
  loadingMore?: boolean;
  savePrompt?: ReactElement | null;
  updateRoundOptions?: ReadonlyArray<{ value: string; label: string }>;
  updateRounds?: string;
  onCreatePlaylist: (source: RecommendationSource) => void;
  onLoadMore?: () => void;
  onUpdateRoundsChange?: (value: string) => void;
  filterCommunities?: TasteCommunityOption[];
  filterError?: string | null;
  filterLoading?: boolean;
  filterPresets?: TastePreset[];
  hasSavedProfileReference?: boolean;
  isAuthenticated?: boolean;
  isReloading?: boolean;
  onEditProfile?: () => void;
  onFilterCommunityWeightsChange?: (weights: Record<string, number>) => void;
  onFilterSettingsChange?: (settings: TasteFilterSettings) => void;
  onPresetSelect?: (preset: TastePreset) => void;
  profileSession?: ProfileSetupResult | null;
}

export function RecommendationList({
  title,
  message,
  source,
  recommendations,
  highlights,
  updateSummary,
  filterSummary,
  canLoadMore = false,
  loadingMore = false,
  savePrompt = null,
  updateRoundOptions,
  updateRounds = "4",
  onCreatePlaylist,
  onLoadMore,
  onUpdateRoundsChange,
  filterCommunities = [],
  filterError = null,
  filterLoading = false,
  filterPresets = [],
  hasSavedProfileReference = false,
  isAuthenticated = false,
  isReloading = false,
  onEditProfile,
  onFilterCommunityWeightsChange,
  onFilterSettingsChange,
  onPresetSelect,
  profileSession = null,
}: RecommendationListProps): ReactElement {
  const showFilterPanel =
    profileSession !== null &&
    onPresetSelect !== undefined &&
    onFilterSettingsChange !== undefined &&
    onFilterCommunityWeightsChange !== undefined &&
    onEditProfile !== undefined;

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

      {savePrompt}

      <div className="results-filter-region">
        <div className="results-toolbar">
          {source === "aktuell" && updateRoundOptions !== undefined && (
            <label className="range-control">
              Zeitraum
              <select
                onChange={(event) => onUpdateRoundsChange?.(event.target.value)}
                value={updateRounds}
              >
                {updateRoundOptions.map((option) => (
                  <option key={option.value} value={option.value}>
                    {option.label}
                  </option>
                ))}
              </select>
            </label>
          )}
          <div className="filter-summary" aria-label="Aktuelle Filter">
            {(filterSummary ?? ["Ausgewogen", "Stilpassung sichtbar"]).map((chip) => (
              <span key={chip}>{chip}</span>
            ))}
          </div>
        </div>

        {showFilterPanel && (
          <ResultsFilterPanel
            communities={filterCommunities}
            error={filterError}
            hasSavedProfileReference={hasSavedProfileReference}
            isAuthenticated={isAuthenticated}
            isReloading={isReloading}
            loading={filterLoading}
            onCommunityWeightsChange={onFilterCommunityWeightsChange}
            onEditProfile={onEditProfile}
            onFilterSettingsChange={onFilterSettingsChange}
            onPresetSelect={onPresetSelect}
            presets={filterPresets}
            profileSession={profileSession}
          />
        )}
      </div>

      {(updateSummary !== undefined || (highlights !== undefined && highlights.length > 0)) && (
        <section
          aria-label="Deine persönliche Auswahl"
          className="personal-recommendations"
        >
          {updateSummary !== undefined && (
            <div className="update-summary">
              <div className="update-summary-lead">
                <p className="eyebrow">Deine persönliche Auswahl</p>
                <h2>{updateSummary.title}</h2>
              </div>
              <p>{updateSummary.description}</p>
            </div>
          )}
          {highlights !== undefined && highlights.length > 0 && (
            <RecommendationHighlights highlights={highlights} />
          )}
        </section>
      )}

      <section aria-labelledby="ranking-heading" className="ranking-section">
        <div className="ranking-heading">
          <h2 id="ranking-heading">Alle Empfehlungen</h2>
          <p>Sortiert nach der Passung zu deinem Musikprofil.</p>
        </div>
        <div className="recommendation-list">
          {recommendations.map((item) => (
            <RecommendationCard key={`${item.source}-${item.rank}`} recommendation={item} />
          ))}
        </div>
        {canLoadMore && onLoadMore !== undefined && (
          <div className="results-load-more">
            <button
              className="secondary-button"
              disabled={loadingMore}
              onClick={onLoadMore}
              type="button"
            >
              {loadingMore ? "Weitere Alben werden geladen ..." : "Weitere Alben laden"}
            </button>
          </div>
        )}
      </section>
    </section>
  );
}
