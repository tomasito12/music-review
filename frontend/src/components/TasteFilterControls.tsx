import type { ReactElement } from "react";

import {
  DEFAULT_YEAR_MAX,
  DEFAULT_YEAR_MIN,
  MAX_PLATTENTESTS_RATING,
  STYLE_MATCH_PERCENT_STEP,
  clampSpectrumCrossover,
  clearYearFilter,
  describeSpectrumCrossover,
  enableYearFilter,
  hasYearFilter,
  overallWeightQuestion,
  readYearBound,
  sortModeLabel,
  styleMatchMinPercent,
  updateFilterSettingsField,
  updateMinimumRating,
  updateStyleMatchMinPercent,
  updateYearFilter,
} from "../lib/filterControls";
import type { TasteCommunityOption, TasteFilterSettings } from "../lib/plattenradarApi";
import { CommunityStyleWeights } from "./CommunityStyleWeights";

interface TasteFilterControlsProps {
  communities: TasteCommunityOption[];
  communityWeights: Record<string, number>;
  filterSettings: TasteFilterSettings;
  onChange: (settings: TasteFilterSettings) => void;
  onCommunityWeightsChange: (weights: Record<string, number>) => void;
  selectedCommunityIds: string[];
}

export function TasteFilterControls({
  communities,
  communityWeights,
  filterSettings,
  onChange,
  onCommunityWeightsChange,
  selectedCommunityIds,
}: TasteFilterControlsProps): ReactElement {
  const yearFilterActive = hasYearFilter(filterSettings);
  const styleMinPercent = styleMatchMinPercent(filterSettings);
  const spectrumValue = clampSpectrumCrossover(
    filterSettings.community_spectrum_crossover,
  );

  return (
    <div className="filter-advanced">
      <details className="filter-panel">
        <summary>Filterung anpassen</summary>
        <p className="field-hint filter-panel-intro">
          Diese Einstellungen bestimmen, welche Alben in den Empfehlungen
          erscheinen. Alben außerhalb der gewählten Bereiche werden ausgeblendet.
        </p>

        <section className="filter-section">
          <h3>Veröffentlichungsjahr</h3>
          {yearFilterActive ? (
            <>
              <div className="year-range-fields">
                <label>
                  Von
                  <input
                    max={DEFAULT_YEAR_MAX}
                    min={DEFAULT_YEAR_MIN}
                    onChange={(event) => {
                      onChange(
                        updateYearFilter(
                          filterSettings,
                          Number(event.target.value),
                          readYearBound(filterSettings, "year_max"),
                        ),
                      );
                    }}
                    step={1}
                    type="number"
                    value={readYearBound(filterSettings, "year_min")}
                  />
                </label>
                <span className="year-range-separator">bis</span>
                <label>
                  Bis
                  <input
                    max={DEFAULT_YEAR_MAX}
                    min={DEFAULT_YEAR_MIN}
                    onChange={(event) => {
                      onChange(
                        updateYearFilter(
                          filterSettings,
                          readYearBound(filterSettings, "year_min"),
                          Number(event.target.value),
                        ),
                      );
                    }}
                    step={1}
                    type="number"
                    value={readYearBound(filterSettings, "year_max")}
                  />
                </label>
              </div>
              <button
                className="ghost-button"
                onClick={() => onChange(clearYearFilter(filterSettings))}
                type="button"
              >
                Alle Erscheinungsjahre zulassen
              </button>
            </>
          ) : (
            <>
              <p className="filter-muted-copy">Aktuell ohne Jahresgrenze.</p>
              <button
                className="secondary-button"
                onClick={() => onChange(enableYearFilter(filterSettings))}
                type="button"
              >
                Zeitraum eingrenzen
              </button>
            </>
          )}
        </section>

        <section className="filter-section">
          <h3>Mindest-Wertung</h3>
          <p className="field-hint">
            Nur Alben mit mindestens dieser plattentests.de-Wertung bleiben in der
            Auswahl.
          </p>
          <label className="threshold-control">
            <span className="threshold-value">
              Mindestens {Math.round(filterSettings.rating_min)}
            </span>
            <input
              max={MAX_PLATTENTESTS_RATING}
              min={0}
              onChange={(event) => {
                onChange(
                  updateMinimumRating(filterSettings, Number(event.target.value)),
                );
              }}
              step={1}
              type="range"
              value={filterSettings.rating_min}
            />
          </label>
        </section>

        <section className="filter-section">
          <h3>Stilpassung</h3>
          <p className="field-hint">
            Alben ab dieser Passung bleiben im Spielraum. Niedrigere Werte öffnen
            die Auswahl für angrenzende Stilrichtungen.
          </p>
          <label className="threshold-control">
            <span className="threshold-value">Mindestens {styleMinPercent} %</span>
            <input
              max={100}
              min={0}
              onChange={(event) => {
                onChange(
                  updateStyleMatchMinPercent(
                    filterSettings,
                    Number(event.target.value),
                  ),
                );
              }}
              step={STYLE_MATCH_PERCENT_STEP}
              type="range"
              value={styleMinPercent}
            />
          </label>
        </section>
      </details>

      <details className="filter-panel">
        <summary>Gewichtung anpassen</summary>
        <p className="field-hint filter-panel-intro">
          Diese Einstellungen beeinflussen die Reihenfolge der Empfehlungen,
          schließen aber keine Alben aus.
        </p>

        <section className="filter-section">
          <h3>Stil-Präferenz</h3>
          <p className="field-hint">
            Steuert, ob stilreine Alben oder Alben mit mehreren passenden
            Stilrichtungen stärker profitieren.
          </p>
          <div className="spectrum-scale-row">
            <span>
              Klare Präferenz:
              <strong> ein gewählter Stil dominiert</strong>
            </span>
            <span className="spectrum-mid">Ausgewogen</span>
            <span>
              Breite Präferenz:
              <strong> möglichst viele Stilrichtungen zugleich</strong>
            </span>
          </div>
          <label className="spectrum-slider threshold-control">
            <span className="threshold-value">
              {describeSpectrumCrossover(spectrumValue)}
            </span>
            <input
              aria-label="Stil-Präferenz"
              max={1}
              min={0}
              onChange={(event) => {
                onChange(
                  updateFilterSettingsField(
                    filterSettings,
                    "community_spectrum_crossover",
                    clampSpectrumCrossover(Number(event.target.value)),
                  ),
                );
              }}
              step={0.05}
              type="range"
              value={spectrumValue}
            />
          </label>
        </section>

        <section className="filter-section">
          <h3>Gewichtung des Gesamtscores</h3>
          {(
            [
              "overall_weight_alpha",
              "overall_weight_beta",
              "overall_weight_gamma",
            ] as const
          ).map((field) => (
            <label className="weight-control" key={field}>
              <span>{overallWeightQuestion(field)}</span>
              <div className="weight-control-row">
                <input
                  max={1}
                  min={0}
                  onChange={(event) => {
                    onChange(
                      updateFilterSettingsField(
                        filterSettings,
                        field,
                        Number(event.target.value),
                      ),
                    );
                  }}
                  step={0.05}
                  type="range"
                  value={filterSettings[field]}
                />
                <span className="threshold-value">
                  {Math.round(filterSettings[field] * 100)} %
                </span>
              </div>
            </label>
          ))}
        </section>

        <section className="filter-section">
          <h3>Gewichte pro Stil-Schwerpunkt</h3>
          <p className="field-hint">
            Hier kannst du bei der Sortierung bestimmte Stilrichtungen stärker oder
            schwächer gewichten.
          </p>
          <CommunityStyleWeights
            communities={communities}
            onChange={onCommunityWeightsChange}
            selectedCommunityIds={selectedCommunityIds}
            weights={communityWeights}
          />
        </section>

        <section className="filter-section">
          <h3>Liste</h3>
          <fieldset className="filter-control">
            <legend>Sortierung</legend>
            <p className="field-hint">
              Standard bleibt stabil. Listenvariation lockert nur die Reihenfolge,
              nicht dein Musikprofil.
            </p>
            <div className="filter-segmented">
              {(["deterministic", "discovery"] as const).map((option) => (
                <button
                  aria-pressed={filterSettings.sort_mode === option}
                  className={filterSettings.sort_mode === option ? "selected" : ""}
                  key={option}
                  onClick={() => {
                    const nextSettings = updateFilterSettingsField(
                      filterSettings,
                      "sort_mode",
                      option,
                    );
                    onChange(
                      option === "deterministic"
                        ? updateFilterSettingsField(nextSettings, "serendipity", 0)
                        : nextSettings,
                    );
                  }}
                  type="button"
                >
                  {sortModeLabel(option)}
                </button>
              ))}
            </div>
          </fieldset>
          <label className="threshold-control">
            <span>Liste variieren</span>
            <p className="field-hint">
              Erhöht, wie stark passende Alben innerhalb der Rangliste neu gemischt
              werden.
            </p>
            <div className="weight-control-row">
              <input
                disabled={filterSettings.sort_mode !== "discovery"}
                max={1}
                min={0}
                onChange={(event) => {
                  onChange(
                    updateFilterSettingsField(
                      filterSettings,
                      "serendipity",
                      Number(event.target.value),
                    ),
                  );
                }}
                step={0.05}
                type="range"
                value={filterSettings.serendipity}
              />
              <span className="threshold-value">
                {Math.round(filterSettings.serendipity * 100)} %
              </span>
            </div>
          </label>
        </section>
      </details>
    </div>
  );
}
