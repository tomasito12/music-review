import { useEffect, useMemo, useState } from "react";
import type { ReactElement } from "react";

import { ApiClient } from "../lib/apiClient";
import {
  normalizeCommunityWeights,
} from "../lib/communityWeightMapping";
import { pickExampleCommunityIds } from "../lib/profileSetupExampleCommunities";
import { formatCommunityExampleArtists } from "../lib/profileFormatting";
import { isProfileStyleMapEnabled } from "../lib/communityStyleMapLayout";
import {
  applyCommunityMapChoice,
  communityChoicesFromLikedIds,
  likedCommunityIds,
  resetCommunityMapChoices,
  summarizeCommunityMapChoices,
  type CommunityMapChoice,
} from "../lib/communityMapChoice";
import type { ProfileEntryContext } from "../lib/profilePageEntry";
import {
  resolveWizardFinishAction,
  resolveWizardPrimaryLabel,
} from "../lib/profileWizardFinish";
import {
  SETUP_STEPS,
  canNavigateToSetupStep,
  type SetupStep,
} from "../lib/profileWizard";
import {
  createTemporaryTasteProfile,
  filterSettingsFromPreset,
  loadArchiveRecommendations,
  loadTasteCommunities,
  loadTasteCommunityMap,
  loadTasteFilterUi,
  loadTastePresets,
} from "../lib/plattenradarApi";
import type {
  TasteCommunityMapNode,
  TasteCommunityOption,
  TasteFilterSettings,
  TasteFilterUiConfig,
  TastePreset,
  TemporaryTasteProfile,
} from "../lib/plattenradarApi";
import type { ProfileSetupResult } from "../lib/profileSessionStorage";
import { TasteFilterControls } from "./TasteFilterControls";
import { CommunityStyleMap } from "./CommunityStyleMap";

interface ProfileSetupShellProps {
  entryContext?: ProfileEntryContext;
  hasReturnRoute?: boolean;
  initialPresetId?: string;
  initialProfile?: TemporaryTasteProfile | null;
  initialStep?: SetupStep;
  isSubmitting: boolean;
  onBackToOverview?: () => void;
  onFinish: (result: ProfileSetupResult) => void;
  onReturnToOverview: (result: ProfileSetupResult) => void;
}

export function ProfileSetupShell({
  entryContext = "initial",
  hasReturnRoute = false,
  initialPresetId,
  initialProfile = null,
  initialStep,
  isSubmitting,
  onBackToOverview,
  onFinish,
  onReturnToOverview,
}: ProfileSetupShellProps): ReactElement {
  const [communities, setCommunities] = useState<TasteCommunityOption[]>([]);
  const [presets, setPresets] = useState<TastePreset[]>([]);
  const [filterUi, setFilterUi] = useState<TasteFilterUiConfig | null>(null);
  const [selectedBroadCategories, setSelectedBroadCategories] = useState<
    string[]
  >([]);
  const [communityChoices, setCommunityChoices] = useState<
    Record<string, CommunityMapChoice>
  >({});
  const [selectedPresetId, setSelectedPresetId] = useState("balanced");
  const [filterSettings, setFilterSettings] = useState<TasteFilterSettings | null>(
    null,
  );
  const [communityWeightsRaw, setCommunityWeightsRaw] = useState<
    Record<string, number>
  >({});
  const [step, setStep] = useState<SetupStep>(initialStep ?? "broad");
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [hydratedFromProfile, setHydratedFromProfile] = useState(false);
  const [archiveMatchTotal, setArchiveMatchTotal] = useState<number | null>(null);
  const [archiveMatchLoading, setArchiveMatchLoading] = useState(false);
  const [mapNodes, setMapNodes] = useState<TasteCommunityMapNode[]>([]);
  const [mapReady, setMapReady] = useState(false);
  const [showDetailsListView, setShowDetailsListView] = useState(false);
  const styleMapEnabled = isProfileStyleMapEnabled();

  const broadCategories = Array.from(
    new Set(
      communities.flatMap((community) => community.broad_categories).filter(Boolean),
    ),
  ).sort((left, right) => left.localeCompare(right, "de"));

  const availableCommunities = communities.filter((community) =>
    community.broad_categories.some((category) =>
      selectedBroadCategories.includes(category),
    ),
  );
  const selectedCommunityIds = useMemo(
    () => likedCommunityIds(communityChoices),
    [communityChoices],
  );
  const choiceSummary = useMemo(
    () =>
      summarizeCommunityMapChoices(
        communityChoices,
        availableCommunities.map((community) => community.id),
      ),
    [availableCommunities, communityChoices],
  );

  const selectedPreset =
    presets.find((preset) => preset.id === selectedPresetId) ?? presets[0] ?? null;

  useEffect(() => {
    let active = true;

    async function loadOptions(): Promise<void> {
      const client = new ApiClient();
      try {
        const [communityOptions, presetOptions, uiConfig, mapData] = await Promise.all([
          loadTasteCommunities(client),
          loadTastePresets(client),
          loadTasteFilterUi(client),
          styleMapEnabled ? loadTasteCommunityMap(client) : Promise.resolve(null),
        ]);
        if (!active) {
          return;
        }
        setCommunities(communityOptions);
        setPresets(presetOptions);
        setFilterUi(uiConfig);
        if (mapData !== null && mapData.nodes.length > 0) {
          setMapNodes(mapData.nodes);
          setMapReady(true);
        } else {
          setMapReady(false);
        }
        const defaultPreset =
          presetOptions.find((preset) => preset.id === uiConfig.default_preset_id) ??
          presetOptions[0];
        if (defaultPreset !== undefined) {
          setSelectedPresetId(defaultPreset.id);
          setFilterSettings(filterSettingsFromPreset(defaultPreset));
        }
        setError(null);
      } catch {
        if (active) {
          setError(
            "Die Stilrichtungen konnten gerade nicht geladen werden. Bitte starte die API mit hatch run api.",
          );
        }
      } finally {
        if (active) {
          setLoading(false);
        }
      }
    }

    void loadOptions();
    return () => {
      active = false;
    };
  }, [styleMapEnabled]);

  useEffect(() => {
    if (
      initialProfile === null ||
      communities.length === 0 ||
      hydratedFromProfile
    ) {
      return;
    }
    const broadCategoriesForProfile = Array.from(
      new Set(
        communities
          .filter((community) =>
            initialProfile.selected_communities.includes(community.id),
          )
          .flatMap((community) => community.broad_categories),
      ),
    );
    setCommunityChoices(
      communityChoicesFromLikedIds(initialProfile.selected_communities),
    );
    setSelectedBroadCategories(broadCategoriesForProfile);
    setFilterSettings(initialProfile.filter_settings);
    setCommunityWeightsRaw(
      normalizeCommunityWeights(
        initialProfile.selected_communities,
        initialProfile.community_weights_raw,
      ),
    );
    if (initialPresetId !== undefined) {
      setSelectedPresetId(initialPresetId);
    }
    if (initialStep !== undefined) {
      setStep(initialStep);
    }
    setHydratedFromProfile(true);
  }, [
    communities,
    hydratedFromProfile,
    initialPresetId,
    initialProfile,
    initialStep,
  ]);

  useEffect(() => {
    setCommunityWeightsRaw((current) =>
      normalizeCommunityWeights(selectedCommunityIds, current),
    );
  }, [selectedCommunityIds]);

  useEffect(() => {
    if (step !== "filters" || selectedCommunityIds.length === 0) {
      setArchiveMatchTotal(null);
      setArchiveMatchLoading(false);
      return;
    }

    const resolvedSettings =
      filterSettings ??
      (selectedPreset !== null ? filterSettingsFromPreset(selectedPreset) : null);
    if (resolvedSettings === null) {
      return;
    }

    let active = true;
    const profile = createTemporaryTasteProfile(
      selectedCommunityIds,
      resolvedSettings,
      communityWeightsRaw,
    );

    async function loadMatchTotal(): Promise<void> {
      setArchiveMatchLoading(true);
      try {
        const result = await loadArchiveRecommendations(new ApiClient(), profile, {
          limit: 1,
          offset: 0,
        });
        if (active) {
          setArchiveMatchTotal(result.total);
        }
      } catch {
        if (active) {
          setArchiveMatchTotal(null);
        }
      } finally {
        if (active) {
          setArchiveMatchLoading(false);
        }
      }
    }

    void loadMatchTotal();
    return () => {
      active = false;
    };
  }, [
    communityWeightsRaw,
    filterSettings,
    selectedCommunityIds,
    selectedPreset,
    step,
  ]);

  function buildProfile(
    settings: TasteFilterSettings | undefined,
  ): TemporaryTasteProfile {
    const resolvedSettings =
      settings ??
      (selectedPreset !== null ? filterSettingsFromPreset(selectedPreset) : undefined);
    return createTemporaryTasteProfile(
      selectedCommunityIds,
      resolvedSettings,
      communityWeightsRaw,
    );
  }

  function buildSetupResult(profile: TemporaryTasteProfile): ProfileSetupResult {
    return {
      profile,
      presetId: selectedPresetId,
      presetLabel: selectedPreset?.label ?? "Ausgewogen",
    };
  }

  function toggleBroadCategory(category: string): void {
    setSelectedBroadCategories((current) => {
      const next = current.includes(category)
        ? current.filter((item) => item !== category)
        : [...current, category];
      const allowedCommunityIds = new Set(
        communities
          .filter((community) =>
            community.broad_categories.some((broadCategory) =>
              next.includes(broadCategory),
            ),
          )
          .map((community) => community.id),
      );
      setCommunityChoices((current) =>
        pruneCommunityMapChoices(
          current,
          Array.from(allowedCommunityIds),
        ),
      );
      return next;
    });
  }

  function toggleCommunity(communityId: string): void {
    setCommunityChoices((current) => {
      const existing = current[communityId] ?? "unset";
      if (existing === "liked") {
        return applyCommunityMapChoice(current, communityId, "unset");
      }
      return applyCommunityMapChoice(current, communityId, "liked");
    });
  }

  function setCommunityChoice(
    communityId: string,
    choice: CommunityMapChoice,
  ): void {
    setCommunityChoices((current) =>
      applyCommunityMapChoice(current, communityId, choice),
    );
  }

  function resetVisibleCommunityChoices(): void {
    if (choiceSummary.reviewed === 0) {
      return;
    }
    const accepted = window.confirm(
      "Alle Bewertungen zurücksetzen? Ausgewählte und abgelehnte Stilwelten werden gelöscht.",
    );
    if (!accepted) {
      return;
    }
    setCommunityChoices((current) =>
      resetCommunityMapChoices(
        current,
        availableCommunities.map((community) => community.id),
      ),
    );
  }

  function selectPreset(presetId: string): void {
    const preset = presets.find((item) => item.id === presetId);
    if (preset === undefined) {
      return;
    }
    setSelectedPresetId(preset.id);
    setFilterSettings(filterSettingsFromPreset(preset));
  }

  function completeWizard(settings: TasteFilterSettings | undefined): void {
    const result = buildSetupResult(buildProfile(settings));
    const finishAction = resolveWizardFinishAction({
      entryContext,
      hasReturnRoute,
    });
    if (finishAction === "returnToOverview") {
      onReturnToOverview(result);
      return;
    }
    onFinish(result);
  }

  function useExampleProfile(): void {
    const accepted = window.confirm(
      "Schnelltest mit drei Beispiel-Stilen starten? Du überspringst die Auswahl und siehst sofort Empfehlungen.",
    );
    if (!accepted) {
      return;
    }
    const exampleIds = pickExampleCommunityIds(communities);
    const settings =
      filterSettings ??
      (selectedPreset !== null
        ? filterSettingsFromPreset(selectedPreset)
        : undefined);
    onFinish(
      buildSetupResult(
        createTemporaryTasteProfile(exampleIds, settings, communityWeightsRaw),
      ),
    );
  }

  function continueWithSelection(): void {
    if (step === "broad") {
      setStep("details");
      return;
    }
    if (step === "details") {
      setStep("filters");
      return;
    }
    const settings =
      filterSettings ??
      (selectedPreset !== null ? filterSettingsFromPreset(selectedPreset) : undefined);
    completeWizard(settings);
  }

  function goBack(): void {
    if (step === "filters") {
      setStep("details");
      return;
    }
    if (step === "details") {
      setStep("broad");
    }
  }

  function navigateToStep(target: SetupStep): void {
    if (
      !canNavigateToSetupStep(step, target, {
        hasBroadSelection: selectedBroadCategories.length > 0,
        hasDetailSelection: selectedCommunityIds.length > 0,
      })
    ) {
      return;
    }
    setStep(target);
  }

  const canContinue =
    step === "broad"
      ? selectedBroadCategories.length > 0
      : step === "details"
        ? selectedCommunityIds.length > 0
        : filterSettings !== null && selectedPreset !== null;

  const primaryLabel = resolveWizardPrimaryLabel({
    step,
    entryContext,
    isSubmitting,
  });
  const showSetupSummary = entryContext === "initial" && step !== "broad";
  const showQuickTest = entryContext === "initial";
  const simplifyInitialFilters = entryContext === "initial";
  const showBackToOverview =
    entryContext === "overview" && onBackToOverview !== undefined;
  const showStyleMap =
    styleMapEnabled && mapReady && !showDetailsListView && step === "details";
  const visibleCommunityIds = availableCommunities.map((community) => community.id);

  return (
    <section className="setup-shell page-shell">
      {showBackToOverview && (
        <div className="setup-overview-back">
          <button className="ghost-button" onClick={onBackToOverview} type="button">
            Zurück zur Übersicht
          </button>
        </div>
      )}
      <div className="setup-progress" aria-label="Musikprofil Fortschritt">
        {SETUP_STEPS.map((progressStep) => {
          const isActive = step === progressStep.id;
          const canNavigate = canNavigateToSetupStep(step, progressStep.id, {
            hasBroadSelection: selectedBroadCategories.length > 0,
            hasDetailSelection: selectedCommunityIds.length > 0,
          });
          return (
            <button
              aria-current={isActive ? "step" : undefined}
              className={`setup-progress-step${
                isActive ? " active" : canNavigate ? " completed" : ""
              }`}
              disabled={!canNavigate}
              key={progressStep.id}
              onClick={() => navigateToStep(progressStep.id)}
              type="button"
            >
              {progressStep.label}
            </button>
          );
        })}
      </div>
      <header className="page-header setup-page-header">
        {step === "broad" && (
          <>
            <h1>Welche groben Richtungen passen zu dir?</h1>
            <p>
              Wähle zuerst die musikalischen Bereiche, aus denen Plattenradar
              passende Detailstile vorschlagen soll.
            </p>
          </>
        )}
        {step === "details" && (
          <>
            <h1>Welche Stilwelten sollen dein Profil prägen?</h1>
            <p>
              Auf der Landkarte liegen ähnliche Referenzwelten nah beieinander.
              Eine Auswahl von etwa 5 bis 15 Stilen reicht meist.
            </p>
          </>
        )}
        {step === "filters" && (
          <>
            <h1>Wie sollen Empfehlungen gewichtet werden?</h1>
            <p>
              {filterUi?.preset_display_hint ??
                "Wähle ein Preset als Startpunkt für Filter und Gewichtung."}
            </p>
          </>
        )}
      </header>
      <div className="setup-grid">
        <div className="setup-panel">
          {step === "broad" && (
            <>
              <div className="choice-grid choice-grid-broad">
                {broadCategories.map((category) => (
                  <button
                    aria-pressed={selectedBroadCategories.includes(category)}
                    className={`choice-card${
                      selectedBroadCategories.includes(category) ? " selected" : ""
                    }`}
                    key={category}
                    onClick={() => toggleBroadCategory(category)}
                    type="button"
                  >
                    <span className="choice-card-label">{category}</span>
                  </button>
                ))}
              </div>
              {selectedBroadCategories.length === 0 && !loading && (
                <p className="field-hint">Wähle mindestens eine Richtung, um fortzufahren.</p>
              )}
            </>
          )}
          {step === "details" && (
            <>
              <div className="setup-details-toolbar">
                <p className="setup-selection-count" aria-live="polite">
                  {showStyleMap ? (
                    <>
                      {choiceSummary.liked} passt · {choiceSummary.disliked} nicht
                      meins · {choiceSummary.unset} noch offen ({choiceSummary.reviewed}{" "}
                      von {choiceSummary.total} bewertet)
                    </>
                  ) : (
                    <>
                      {selectedCommunityIds.length} von {availableCommunities.length}{" "}
                      Stilwelten ausgewählt
                    </>
                  )}
                </p>
                <div className="setup-details-toolbar-actions">
                  {choiceSummary.reviewed > 0 && (
                    <button
                      className="ghost-button setup-details-reset"
                      onClick={resetVisibleCommunityChoices}
                      type="button"
                    >
                      Auswahl zurücksetzen
                    </button>
                  )}
                  {styleMapEnabled && mapReady && (
                    <button
                      className="ghost-button setup-details-view-toggle"
                      onClick={() => setShowDetailsListView((current) => !current)}
                      type="button"
                    >
                      {showDetailsListView ? "Landkarte anzeigen" : "Listenansicht"}
                    </button>
                  )}
                </div>
              </div>
              {selectedCommunityIds.length > 15 && (
                <p className="field-hint setup-selection-hint">
                  Viele Stile — Empfehlungen werden breiter.
                </p>
              )}
              {showStyleMap && (
                <div className="setup-details-map-desktop">
                  <CommunityStyleMap
                    communities={availableCommunities}
                    communityChoices={communityChoices}
                    mapNodes={mapNodes}
                    onSetCommunityChoice={setCommunityChoice}
                    visibleCommunityIds={visibleCommunityIds}
                  />
                </div>
              )}
              <div
                className={`choice-grid choice-grid-details${
                  showStyleMap ? " setup-details-list-fallback" : ""
                }`}
              >
                {availableCommunities.map((community) => {
                  const exampleCaption = formatCommunityExampleArtists(
                    community.example_artists,
                  );
                  return (
                    <button
                      aria-pressed={selectedCommunityIds.includes(community.id)}
                      className={`choice-card${
                        selectedCommunityIds.includes(community.id) ? " selected" : ""
                      }`}
                      key={community.id}
                      onClick={() => toggleCommunity(community.id)}
                      type="button"
                    >
                      <span>{community.label}</span>
                      {exampleCaption !== "" && <small>{exampleCaption}</small>}
                    </button>
                  );
                })}
              </div>
            </>
          )}
          {step === "filters" && (
            <>
              <div className="preset-grid">
                {presets.map((preset) => (
                  <button
                    aria-pressed={selectedPresetId === preset.id}
                    className={`preset-card${
                      selectedPresetId === preset.id ? " selected" : ""
                    }`}
                    key={preset.id}
                    onClick={() => selectPreset(preset.id)}
                    type="button"
                  >
                    <strong>{preset.label}</strong>
                    <span>{preset.subtitle}</span>
                    <p>{preset.description}</p>
                  </button>
                ))}
              </div>
              {simplifyInitialFilters && (
                <p className="field-hint setup-filter-hint">
                  Feintuning kannst du später auf Aktuell und Entdecken vornehmen.
                </p>
              )}
              {archiveMatchLoading && (
                <p className="field-hint setup-match-total">Treffer werden berechnet ...</p>
              )}
              {!archiveMatchLoading && archiveMatchTotal !== null && (
                <p className="setup-match-total">
                  Etwa {archiveMatchTotal.toLocaleString("de-DE")} Alben im Archiv passen zu
                  dieser Auswahl.
                </p>
              )}
              {filterSettings !== null &&
                (simplifyInitialFilters ? (
                  <details className="setup-advanced-filters">
                    <summary>Erweitert anpassen</summary>
                    <TasteFilterControls
                      communities={communities}
                      communityWeights={communityWeightsRaw}
                      filterSettings={filterSettings}
                      onChange={setFilterSettings}
                      onCommunityWeightsChange={setCommunityWeightsRaw}
                      selectedCommunityIds={selectedCommunityIds}
                    />
                  </details>
                ) : (
                  <TasteFilterControls
                    communities={communities}
                    communityWeights={communityWeightsRaw}
                    filterSettings={filterSettings}
                    onChange={setFilterSettings}
                    onCommunityWeightsChange={setCommunityWeightsRaw}
                    selectedCommunityIds={selectedCommunityIds}
                  />
                ))}
            </>
          )}
          {loading && <p className="field-hint">Stilrichtungen werden geladen ...</p>}
          {error !== null && <p className="form-error">{error}</p>}
          <div className="welcome-actions">
            {step !== "broad" && (
              <button
                className="secondary-button"
                disabled={isSubmitting}
                onClick={goBack}
                type="button"
              >
                Zurück
              </button>
            )}
            <button
              className="primary-button"
              disabled={!canContinue || isSubmitting || loading}
              onClick={continueWithSelection}
              type="button"
            >
              {primaryLabel}
            </button>
            {showQuickTest && (
              <button
                className="ghost-button"
                disabled={communities.length === 0 || isSubmitting || loading}
                onClick={useExampleProfile}
                title="Überspringt die Auswahl und zeigt Empfehlungen mit drei Beispiel-Stilen."
                type="button"
              >
                Schnelltest: Beispiel-Stile
              </button>
            )}
          </div>
        </div>
        {showSetupSummary && (
          <aside className="setup-summary setup-summary-subtle">
            <h2>Dein Profil</h2>
            <div className="setup-summary-section">
              <strong>Richtungen</strong>
              <span>{selectedBroadCategories.join(", ")}</span>
            </div>
            <div className="setup-summary-section">
              <strong>Detailstile</strong>
              <span>
                {selectedCommunityIds.length > 0
                  ? `${selectedCommunityIds.length} ausgewählt`
                  : "Noch keine Auswahl"}
              </span>
            </div>
            {step === "filters" && (
              <div className="setup-summary-section">
                <strong>Preset</strong>
                <span>{selectedPreset?.label ?? "Ausgewogen"}</span>
              </div>
            )}
          </aside>
        )}
      </div>
    </section>
  );
}
