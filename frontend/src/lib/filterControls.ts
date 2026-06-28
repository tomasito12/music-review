import type { TasteFilterSettings } from "./plattenradarApi";

export const DEFAULT_YEAR_MIN = 1970;
export const DEFAULT_YEAR_MAX = 2026;
export const DEFAULT_MIN_RATING = 6;
export const MAX_PLATTENTESTS_RATING = 10;
export const STYLE_MATCH_PERCENT_STEP = 5;

export const SPECTRUM_CROSSOVER_STOPS = [0, 0.25, 0.5, 0.75, 1] as const;

const SPECTRUM_CROSSOVER_LABELS: Record<number, string> = {
  0: "Starker Stil-Fokus",
  0.25: "Eher Fokus",
  0.5: "Ausgewogen",
  0.75: "Eher Breite",
  1: "Breite Abdeckung",
};

const SORT_MODE_LABELS: Record<string, string> = {
  deterministic: "Stabile Reihenfolge",
  discovery: "Mit Zufall",
};

const OVERALL_WEIGHT_QUESTIONS: Record<string, string> = {
  overall_weight_alpha:
    "Wie wichtig ist dir, dass die Sortierung deinen gewählten Musikrichtungen entspricht?",
  overall_weight_beta:
    "Wie wichtig ist dir, dass höher bewertete Alben weiter oben in der Sortierung stehen?",
  overall_weight_gamma:
    "Wie wichtig ist dir, dass Alben mit mehreren passenden Stilrichtungen weiter oben stehen?",
};

/** Returns a human-readable label for one sort mode option. */
export function sortModeLabel(value: string): string {
  return SORT_MODE_LABELS[value] ?? value;
}

/** Returns a readable label for any crossover value on the continuous scale. */
export function describeSpectrumCrossover(value: number): string {
  return spectrumCrossoverLabel(value);
}

/** Clamps a crossover value to the valid 0..1 range without snapping to stops. */
export function clampSpectrumCrossover(value: number): number {
  return Math.min(1, Math.max(0, value));
}

/** Returns the German label for the nearest crossover stop. */
export function spectrumCrossoverLabel(value: number): string {
  const snapped = snapSpectrumCrossover(value);
  return SPECTRUM_CROSSOVER_LABELS[snapped] ?? "Ausgewogen";
}

/** Snaps a crossover value to the nearest named stop for summaries. */
export function snapSpectrumCrossover(value: number): number {
  const clamped = clampSpectrumCrossover(value);
  return SPECTRUM_CROSSOVER_STOPS.reduce((best, stop) =>
    Math.abs(stop - clamped) < Math.abs(best - clamped) ? stop : best,
  );
}

/** Returns the question text for one overall-weight slider. */
export function overallWeightQuestion(field: string): string {
  return OVERALL_WEIGHT_QUESTIONS[field] ?? field;
}

/** Reads the minimum style-match threshold as a whole percent value. */
export function styleMatchMinPercent(settings: TasteFilterSettings): number {
  return Math.round(settings.score_min * 100);
}

/** Updates the minimum style-match threshold from a percent slider. */
export function updateStyleMatchMinPercent(
  settings: TasteFilterSettings,
  percent: number,
): TasteFilterSettings {
  const snapped =
    Math.round(percent / STYLE_MATCH_PERCENT_STEP) * STYLE_MATCH_PERCENT_STEP;
  const bounded = Math.min(100, Math.max(0, snapped));
  return {
    ...settings,
    score_min: bounded / 100,
    score_max: 1,
  };
}

/** Updates the minimum plattentests.de rating while keeping the upper bound open. */
export function updateMinimumRating(
  settings: TasteFilterSettings,
  ratingMin: number,
): TasteFilterSettings {
  const bounded = Math.min(
    MAX_PLATTENTESTS_RATING,
    Math.max(0, Math.round(ratingMin)),
  );
  return {
    ...settings,
    rating_min: bounded,
    rating_max: MAX_PLATTENTESTS_RATING,
  };
}

/** Returns whether a year filter is currently active. */
export function hasYearFilter(settings: TasteFilterSettings): boolean {
  return settings.year_min !== null && settings.year_min !== undefined;
}

/** Reads one year bound for display, using corpus defaults when unset. */
export function readYearBound(
  settings: TasteFilterSettings,
  field: "year_min" | "year_max",
): number {
  const value = settings[field];
  if (typeof value === "number") {
    return value;
  }
  return field === "year_min" ? DEFAULT_YEAR_MIN : DEFAULT_YEAR_MAX;
}

/** Activates a year filter with corpus defaults. */
export function enableYearFilter(
  settings: TasteFilterSettings,
): TasteFilterSettings {
  return {
    ...settings,
    year_min: DEFAULT_YEAR_MIN,
    year_max: DEFAULT_YEAR_MAX,
  };
}

/** Clears the year filter so all release years remain eligible. */
export function clearYearFilter(settings: TasteFilterSettings): TasteFilterSettings {
  return {
    ...settings,
    year_min: null,
    year_max: null,
  };
}

/** Updates both ends of the year filter. */
export function updateYearFilter(
  settings: TasteFilterSettings,
  yearMin: number,
  yearMax: number,
): TasteFilterSettings {
  const orderedMin = Math.min(yearMin, yearMax);
  const orderedMax = Math.max(yearMin, yearMax);
  return {
    ...settings,
    year_min: orderedMin,
    year_max: orderedMax,
  };
}

/** Updates one filter field and returns a new settings object. */
export function updateFilterSettingsField(
  settings: TasteFilterSettings,
  field: keyof TasteFilterSettings,
  value: number | string | null,
): TasteFilterSettings {
  return {
    ...settings,
    [field]: value,
  };
}

/** Formats a score threshold as a whole-number percent label. */
export function formatScorePercent(value: number): string {
  return `${Math.round(value * 100)} %`;
}
