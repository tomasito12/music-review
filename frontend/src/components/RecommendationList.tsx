import { useCallback, useEffect, useState, type ReactElement } from "react";

import type {
  Recommendation,
  RecommendationHighlight,
  RecommendationSource,
} from "../types";
import type { AktuellBriefing } from "../lib/aktuellPage";
import { entdeckenHighlightArtistLookupKeys } from "../lib/entdeckenPage";
import type { TasteCommunityOption, TasteFilterSettings, TastePreset } from "../lib/plattenradarApi";
import type { ProfileSetupResult } from "../lib/profileSessionStorage";

import { AktuellRankingList } from "./AktuellRankingList";
import { EntdeckenHighlightsSection } from "./EntdeckenHighlightsSection";
import { EntdeckenRankingList } from "./EntdeckenRankingList";
import { RecommendationHighlights } from "./RecommendationHighlights";
import { ResultsFilterPanel } from "./ResultsFilterPanel";
import { ResultsListPrelude } from "./ResultsListPrelude";
import {
  shouldShowResultsListPrelude,
  shouldShowStandaloneFilterRegion,
} from "../lib/resultsListLayout";

interface RecommendationListProps {
  aktuellBriefing?: AktuellBriefing;
  title: string;
  message: string;
  source: RecommendationSource;
  recommendations: Recommendation[];
  highlights?: RecommendationHighlight[];
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
  aktuellBriefing,
  title,
  message,
  source,
  recommendations,
  highlights,
  filterSummary,
  canLoadMore = false,
  loadingMore = false,
  savePrompt = null,
  updateRoundOptions,
  updateRounds = "1",
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
  const [entdeckenHighlights, setEntdeckenHighlights] = useState<RecommendationHighlight[]>([]);
  const [entdeckenHighlightsResolved, setEntdeckenHighlightsResolved] = useState(false);
  const [rankingReady, setRankingReady] = useState(false);

  useEffect(() => {
    if (!isReloading) {
      return;
    }
    if (source === "entdecken") {
      setEntdeckenHighlights([]);
      setEntdeckenHighlightsResolved(false);
    }
    setRankingReady(false);
  }, [isReloading, source]);

  const handleEntdeckenHighlightsResolved = useCallback(
    (resolved: RecommendationHighlight[]) => {
      setEntdeckenHighlights(resolved);
      setEntdeckenHighlightsResolved(true);
    },
    [],
  );

  const handleRankingReady = useCallback(() => {
    setRankingReady(true);
  }, []);

  const showFilterPanel =
    profileSession !== null &&
    onPresetSelect !== undefined &&
    onFilterSettingsChange !== undefined &&
    onFilterCommunityWeightsChange !== undefined &&
    onEditProfile !== undefined;
  const aktuellHighlights =
    source === "aktuell" && highlights !== undefined && highlights.length > 0
      ? highlights
      : undefined;
  const activeHighlights =
    source === "entdecken"
      ? entdeckenHighlights.length > 0
        ? entdeckenHighlights
        : undefined
      : aktuellHighlights;
  const topRecommendationIds = new Set(
    (activeHighlights ?? []).map(
      (highlight) =>
        `${highlight.recommendation.artist}-${highlight.recommendation.album}`,
    ),
  );
  const listRecommendations =
    activeHighlights !== undefined && recommendations.length > topRecommendationIds.size
      ? recommendations.filter(
          (item) => !topRecommendationIds.has(`${item.artist}-${item.album}`),
        )
      : recommendations;
  const hasEditorialHighlights = activeHighlights !== undefined && activeHighlights.length > 0;
  const showEntdeckenHero = source === "entdecken" && recommendations.length > 0;
  const showPrelude = shouldShowResultsListPrelude(activeHighlights ?? []);
  const showStandaloneFilters = shouldShowStandaloneFilterRegion(
    showFilterPanel,
    showPrelude,
  );
  const entdeckenExcludedArtistLookupKeys =
    source === "entdecken" && activeHighlights !== undefined
      ? entdeckenHighlightArtistLookupKeys(activeHighlights)
      : new Set<string>();
  const visualPageReady =
    source === "entdecken"
      ? entdeckenHighlightsResolved && rankingReady
      : source === "aktuell"
        ? rankingReady
        : false;
  const filterRegion = (
    <div
      className={`results-filter-region${
        hasEditorialHighlights ? " results-filter-region-after-highlights" : ""
      }`}
    >
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
        {isReloading && (
          <span className="results-reload-chip" role="status">
            Aktualisiere ...
          </span>
        )}
      </div>

      {showFilterPanel && (
        <ResultsFilterPanel
          communities={filterCommunities}
          error={filterError}
          hasSavedProfileReference={hasSavedProfileReference}
          isAuthenticated={isAuthenticated}
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
  );

  return (
    <section className="results-page page-shell">
      {aktuellBriefing !== undefined ? (
        <section className="aktuell-briefing" aria-labelledby="aktuell-heading">
          <div className="aktuell-briefing-toolbar">
            <button
              className="primary-button"
              onClick={() => onCreatePlaylist(source)}
              type="button"
            >
              Playlist aus Neuheiten vorbereiten
            </button>
          </div>
          <div className="aktuell-briefing-copy">
            <p className="eyebrow">{aktuellBriefing.kicker}</p>
            <h1 id="aktuell-heading">{aktuellBriefing.title}</h1>
            <p>{aktuellBriefing.description}</p>
          </div>
        </section>
      ) : (
        <div className="results-header">
          <header className="page-header">
            <p className="eyebrow">
              {source === "aktuell" ? "Neuheiten" : "Archiv"}
            </p>
            <h1>{title}</h1>
            <p>{message}</p>
          </header>
          <button
            className="primary-button"
            onClick={() => onCreatePlaylist(source)}
            type="button"
          >
            Playlist erzeugen
          </button>
        </div>
      )}

      {savePrompt}

      <div
        className={`results-body${
          isReloading ? " results-reloading" : ""
        }${source === "aktuell" ? " results-body-aktuell" : ""}${
          source === "entdecken" ? " results-body-entdecken" : ""
        }`}
        data-visual-page-ready={visualPageReady ? "true" : "pending"}
      >
        {showEntdeckenHero && (
          <EntdeckenHighlightsSection
            onHighlightsResolved={handleEntdeckenHighlightsResolved}
            recommendations={recommendations}
            showSaveAction
          />
        )}

        {source === "aktuell" && aktuellHighlights !== undefined && (
          <RecommendationHighlights highlights={aktuellHighlights} showSaveAction />
        )}

        {showPrelude && (
          <ResultsListPrelude filterRegion={filterRegion} source={source} />
        )}

        {showStandaloneFilters && filterRegion}

        {source === "entdecken" ? (
          entdeckenHighlightsResolved ? (
            <EntdeckenRankingList
              canLoadMore={canLoadMore}
              excludedArtistLookupKeys={entdeckenExcludedArtistLookupKeys}
              loadingMore={loadingMore}
              onLoadMore={onLoadMore}
              onRankingReady={handleRankingReady}
              recommendations={listRecommendations}
              showSaveAction
            />
          ) : null
        ) : (
          <AktuellRankingList
            canLoadMore={canLoadMore}
            loadingMore={loadingMore}
            onLoadMore={onLoadMore}
            onRankingReady={handleRankingReady}
            recommendations={listRecommendations}
            showSaveAction
          />
        )}
      </div>
    </section>
  );
}
