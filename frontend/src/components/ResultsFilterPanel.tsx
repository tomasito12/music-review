import type { ReactElement } from "react";

import type { TasteCommunityOption, TasteFilterSettings, TastePreset } from "../lib/plattenradarApi";
import type { ProfileSetupResult } from "../lib/profileSessionStorage";

import { PresetPillBar } from "./PresetPillBar";
import { TasteFilterControls } from "./TasteFilterControls";

interface ResultsFilterPanelProps {
  communities: TasteCommunityOption[];
  error: string | null;
  hasSavedProfileReference: boolean;
  isAuthenticated: boolean;
  isReloading: boolean;
  loading: boolean;
  onCommunityWeightsChange: (weights: Record<string, number>) => void;
  onEditProfile: () => void;
  onFilterSettingsChange: (settings: TasteFilterSettings) => void;
  onPresetSelect: (preset: TastePreset) => void;
  presets: TastePreset[];
  profileSession: ProfileSetupResult;
}

export function ResultsFilterPanel({
  communities,
  error,
  hasSavedProfileReference,
  isAuthenticated,
  isReloading,
  loading,
  onCommunityWeightsChange,
  onEditProfile,
  onFilterSettingsChange,
  onPresetSelect,
  presets,
  profileSession,
}: ResultsFilterPanelProps): ReactElement {
  const { profile } = profileSession;

  const introText =
    isAuthenticated && hasSavedProfileReference
      ? "Änderungen wirken sofort auf diese Liste. Dauerhaft speichern kannst du sie oben im Banner."
      : "Änderungen wirken sofort auf diese Liste.";

  return (
    <div className="results-filter-shell">
      {!loading && presets.length > 0 && (
        <PresetPillBar
          onSelect={onPresetSelect}
          presets={presets}
          selectedPresetId={profileSession.presetId}
        />
      )}
      {loading && (
        <p className="field-hint results-filter-loading">Filter werden geladen ...</p>
      )}
      {error !== null && <p className="form-error">{error}</p>}
      {isReloading && (
        <p aria-live="polite" className="field-hint results-filter-reloading">
          Empfehlungen werden aktualisiert ...
        </p>
      )}

      <details className="results-filter-panel">
        <summary>Filter und Gewichtung anpassen</summary>
        <p className="field-hint filter-panel-intro">{introText}</p>
        {!loading && communities.length > 0 && (
          <TasteFilterControls
            communities={communities}
            communityWeights={profile.community_weights_raw}
            filterSettings={profile.filter_settings}
            onChange={onFilterSettingsChange}
            onCommunityWeightsChange={onCommunityWeightsChange}
            selectedCommunityIds={profile.selected_communities}
            sliderApplyMode="commit"
          />
        )}
        <p className="results-filter-profile-link">
          <button className="link-button" onClick={onEditProfile} type="button">
            Stilrichtungen im Musikprofil bearbeiten
          </button>
        </p>
      </details>
    </div>
  );
}
