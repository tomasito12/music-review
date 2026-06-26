import { ApiClient } from "./apiClient";

import type { Recommendation, RecommendationTag } from "../types";

export interface TasteCommunityOption {
  broad_categories: string[];
  example_artists: string[];
  id: string;
  label: string;
}

export interface TasteFilterSettings {
  community_spectrum_crossover: number;
  overall_weight_alpha: number;
  overall_weight_beta: number;
  overall_weight_gamma: number;
  rating_max: number;
  rating_min: number;
  score_max: number;
  score_min: number;
  serendipity: number;
  sort_mode: string;
  year_max?: number | null;
  year_min?: number | null;
}

export interface TastePreset {
  description: string;
  filter_settings: TasteFilterSettings;
  icon: string;
  id: string;
  label: string;
  subtitle: string;
}

export interface FilterControl {
  description: string;
  expert: boolean;
  fields: string[];
  id: string;
  kind: string;
  label: string;
  max_value: number | null;
  min_value: number | null;
  options: string[];
  step: number | null;
}

export interface FilterGroup {
  controls: FilterControl[];
  description: string;
  id: string;
  label: string;
}

export interface TasteFilterUiConfig {
  default_preset_id: string;
  groups: FilterGroup[];
  preset_display: string;
  preset_display_hint: string;
}

export interface TemporaryTasteProfile {
  community_weights_raw: Record<string, number>;
  filter_settings: TasteFilterSettings;
  name: string;
  selected_communities: string[];
}

interface ApiCommunityMatch {
  affinity: number;
  id: string;
  label: string;
  matched: boolean;
}

interface ApiRecommendation {
  album: string;
  artist: string;
  labels: string;
  matched_tags: ApiCommunityMatch[];
  overall_score: number;
  rank: number;
  rating: number | null;
  source: "archive" | "new_reviews";
  text_excerpt: string;
  url: string | null;
  year: number | null;
}

interface ApiRecommendationSet {
  items: ApiRecommendation[];
  total: number;
}

export const ARCHIVE_PAGE_SIZE = 20;

export interface ArchivePageRequest {
  limit?: number;
  offset?: number;
}

/** Balanced defaults used when presets are not loaded yet. */
export const DEFAULT_BALANCED_FILTER_SETTINGS: TasteFilterSettings = {
  rating_min: 6,
  rating_max: 10,
  score_min: 0.4,
  score_max: 1,
  overall_weight_alpha: 0.5,
  overall_weight_beta: 0.25,
  overall_weight_gamma: 0.25,
  community_spectrum_crossover: 0.5,
  sort_mode: "deterministic",
  serendipity: 0,
};

/** Loads selectable music styles from the Plattenradar API. */
export async function loadTasteCommunities(
  client: ApiClient,
): Promise<TasteCommunityOption[]> {
  return client.get<TasteCommunityOption[]>("/v1/taste-communities");
}

/** Loads taste presets for the profile setup step. */
export async function loadTastePresets(client: ApiClient): Promise<TastePreset[]> {
  return client.get<TastePreset[]>("/v1/presets");
}

/** Loads filter UI metadata (labels and grouping). */
export async function loadTasteFilterUi(
  client: ApiClient,
): Promise<TasteFilterUiConfig> {
  return client.get<TasteFilterUiConfig>("/v1/taste-filter-ui");
}

/** Loads one page of archive recommendations for a temporary taste profile. */
export async function loadArchiveRecommendations(
  client: ApiClient,
  profile: TemporaryTasteProfile,
  page: ArchivePageRequest = {},
): Promise<{ recommendations: Recommendation[]; total: number }> {
  const limit = page.limit ?? ARCHIVE_PAGE_SIZE;
  const offset = page.offset ?? 0;
  const response = await client.post<ApiRecommendationSet>(
    "/v1/recommendations/archive",
    { profile, limit, offset },
  );
  return {
    recommendations: response.items.map(toRecommendation),
    total: response.total,
  };
}

/** Returns filter settings copied from a preset definition. */
export function filterSettingsFromPreset(preset: TastePreset): TasteFilterSettings {
  return normalizeFilterSettings(preset.filter_settings);
}

/** Creates a temporary profile from community selection and filter settings. */
export function createTemporaryTasteProfile(
  selectedCommunities: string[],
  filterSettings: TasteFilterSettings = DEFAULT_BALANCED_FILTER_SETTINGS,
): TemporaryTasteProfile {
  return {
    name: "Temporäres Musikprofil",
    selected_communities: selectedCommunities,
    community_weights_raw: Object.fromEntries(
      selectedCommunities.map((communityId) => [communityId, 1]),
    ),
    filter_settings: normalizeFilterSettings(filterSettings),
  };
}

function normalizeFilterSettings(
  settings: Partial<TasteFilterSettings>,
): TasteFilterSettings {
  return {
    rating_min: settings.rating_min ?? DEFAULT_BALANCED_FILTER_SETTINGS.rating_min,
    rating_max: settings.rating_max ?? DEFAULT_BALANCED_FILTER_SETTINGS.rating_max,
    score_min: settings.score_min ?? DEFAULT_BALANCED_FILTER_SETTINGS.score_min,
    score_max: settings.score_max ?? DEFAULT_BALANCED_FILTER_SETTINGS.score_max,
    overall_weight_alpha:
      settings.overall_weight_alpha ??
      DEFAULT_BALANCED_FILTER_SETTINGS.overall_weight_alpha,
    overall_weight_beta:
      settings.overall_weight_beta ?? DEFAULT_BALANCED_FILTER_SETTINGS.overall_weight_beta,
    overall_weight_gamma:
      settings.overall_weight_gamma ??
      DEFAULT_BALANCED_FILTER_SETTINGS.overall_weight_gamma,
    community_spectrum_crossover:
      settings.community_spectrum_crossover ??
      DEFAULT_BALANCED_FILTER_SETTINGS.community_spectrum_crossover,
    sort_mode: settings.sort_mode ?? DEFAULT_BALANCED_FILTER_SETTINGS.sort_mode,
    serendipity: settings.serendipity ?? DEFAULT_BALANCED_FILTER_SETTINGS.serendipity,
    year_min: settings.year_min ?? null,
    year_max: settings.year_max ?? null,
  };
}

function toRecommendation(item: ApiRecommendation): Recommendation {
  const tags = item.matched_tags.map(toRecommendationTag);
  const fitPercent = Math.round(item.overall_score * 100);
  return {
    rank: item.rank,
    artist: item.artist,
    album: item.album,
    year: item.year ?? 0,
    rating: item.rating ?? 0,
    score: item.overall_score,
    fitLabel: fitLabel(item.overall_score),
    fitPercent,
    recordLabel: item.labels || undefined,
    excerpt: item.text_excerpt,
    reviewUrl: item.url ?? "https://www.plattentests.de/",
    tags,
    source: "entdecken",
  };
}

function toRecommendationTag(tag: ApiCommunityMatch): RecommendationTag {
  return {
    label: tag.label,
    matchesProfile: tag.matched,
    strength: tag.affinity >= 0.7 ? "high" : tag.affinity >= 0.35 ? "medium" : "low",
  };
}

function fitLabel(score: number): string {
  if (score >= 0.75) {
    return "Sehr passend";
  }
  if (score >= 0.4) {
    return "Passend";
  }
  return "Interessanter Randbereich";
}
