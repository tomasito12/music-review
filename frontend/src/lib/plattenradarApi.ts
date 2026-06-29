import { ApiClient } from "./apiClient";
import {
  DEFAULT_COMMUNITY_WEIGHT_RAW,
  migrateLegacyCommunityWeights,
  normalizeCommunityWeights,
} from "./communityWeightMapping";
import type {
  PlaylistExportRequestOptions,
  PlaylistExportResult,
} from "./playlistExport";
import { buildPlaylistExportPayload } from "./playlistExport";

import type { Recommendation, RecommendationTag, SavedAlbum } from "../types";

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

export interface AuthUser {
  email: string;
  slug: string;
}

interface AuthTokenResponse {
  access_token: string;
  token_type: string;
  user: AuthUser;
}

export interface ApiTasteProfilePayload {
  community_weights_raw: Record<string, number>;
  filter_settings: TasteFilterSettings;
  name: string;
  selected_communities: string[];
}

interface TasteProfileResponse {
  profile: ApiTasteProfilePayload | null;
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
  artist_mbid: string | null;
  labels: string;
  matched_tags: ApiCommunityMatch[];
  overall_score: number;
  rank: number;
  rating: number | null;
  release_date: string | null;
  review_id: number;
  source: "archive" | "new_reviews";
  text_excerpt: string;
  text_excerpt_continues?: boolean;
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

export interface NewReviewsPageRequest extends ArchivePageRequest {
  newestCount?: number;
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

/** Converts a temporary frontend profile into an API taste-profile payload. */
export function temporaryProfileToApi(
  profile: TemporaryTasteProfile,
): ApiTasteProfilePayload {
  return {
    name: profile.name,
    selected_communities: [...profile.selected_communities],
    community_weights_raw: { ...profile.community_weights_raw },
    filter_settings: normalizeFilterSettings(profile.filter_settings),
  };
}

/** Converts a stored API profile into the temporary frontend shape. */
export function apiProfileToTemporary(
  profile: ApiTasteProfilePayload,
): TemporaryTasteProfile {
  return {
    name: profile.name,
    selected_communities: [...profile.selected_communities],
    community_weights_raw: migrateLegacyCommunityWeights(
      normalizeCommunityWeights(
        [...profile.selected_communities],
        profile.community_weights_raw,
      ),
    ),
    filter_settings: normalizeFilterSettings(profile.filter_settings),
  };
}

/** Registers a new account and optionally stores a taste profile. */
export async function registerAccount(
  client: ApiClient,
  email: string,
  password: string,
  profile?: TemporaryTasteProfile,
): Promise<{ token: string; user: AuthUser }> {
  const response = await client.post<AuthTokenResponse>("/v1/auth/register", {
    email,
    password,
    profile:
      profile === undefined ? undefined : temporaryProfileToApi(profile),
  });
  return {
    token: response.access_token,
    user: response.user,
  };
}

/** Logs in with email and password. */
export async function loginAccount(
  client: ApiClient,
  email: string,
  password: string,
): Promise<{ token: string; user: AuthUser }> {
  const response = await client.post<AuthTokenResponse>("/v1/auth/login", {
    email,
    password,
  });
  return {
    token: response.access_token,
    user: response.user,
  };
}

/** Returns the authenticated user for a bearer token. */
export async function fetchCurrentUser(client: ApiClient): Promise<AuthUser> {
  return client.get<AuthUser>("/v1/me");
}

/** Loads the saved taste profile for the authenticated user. */
export async function fetchSavedTasteProfile(
  client: ApiClient,
): Promise<TemporaryTasteProfile | null> {
  const response = await client.get<TasteProfileResponse>("/v1/me/taste-profile");
  if (response.profile === null) {
    return null;
  }
  return apiProfileToTemporary(response.profile);
}

/** Replaces the authenticated user's saved taste profile. */
export async function saveTasteProfile(
  client: ApiClient,
  profile: TemporaryTasteProfile,
): Promise<TemporaryTasteProfile> {
  const response = await client.put<TasteProfileResponse>(
    "/v1/me/taste-profile",
    temporaryProfileToApi(profile),
  );
  if (response.profile === null) {
    throw new Error("Taste profile was not saved.");
  }
  return apiProfileToTemporary(response.profile);
}

interface ApiSavedAlbum {
  review_id: number;
  artist: string;
  album: string;
  review_url: string;
  source: "archive" | "new_reviews" | null;
  saved_at: string;
}

interface ApiFavoritesListResponse {
  items: ApiSavedAlbum[];
}

interface ApiMergeFavoritesResponse {
  merged_count: number;
}

export interface SaveFavoritePayload {
  artist: string;
  album: string;
  review_url: string;
  source: "archive" | "new_reviews" | null;
}

export interface MergeFavoritePayload extends SaveFavoritePayload {
  review_id: number;
  saved_at?: string;
}

/** Loads saved albums for the authenticated user. */
export async function fetchFavorites(client: ApiClient): Promise<SavedAlbum[]> {
  const response = await client.get<ApiFavoritesListResponse>("/v1/me/favorites");
  return response.items.map(toSavedAlbum);
}

/** Saves one album for the authenticated user. */
export async function saveFavorite(
  client: ApiClient,
  reviewId: number,
  payload: SaveFavoritePayload,
): Promise<SavedAlbum> {
  const response = await client.put<ApiSavedAlbum>(
    `/v1/me/favorites/${reviewId}`,
    payload,
  );
  return toSavedAlbum(response);
}

/** Removes one saved album for the authenticated user. */
export async function removeFavorite(
  client: ApiClient,
  reviewId: number,
): Promise<void> {
  await client.delete(`/v1/me/favorites/${reviewId}`);
}

/** Merges guest favorites into the authenticated user account. */
export async function mergeFavorites(
  client: ApiClient,
  items: MergeFavoritePayload[],
): Promise<number> {
  const response = await client.post<ApiMergeFavoritesResponse>(
    "/v1/me/favorites/merge",
    { items },
  );
  return response.merged_count;
}

/** Maps a UI recommendation source to the API favorite source value. */
export function recommendationSourceToApiSource(
  source: Recommendation["source"],
): "archive" | "new_reviews" {
  return source === "aktuell" ? "new_reviews" : "archive";
}

/** Maps an API favorite source to the UI recommendation source. */
export function apiSourceToRecommendationSource(
  source: "archive" | "new_reviews" | null,
): Recommendation["source"] | null {
  if (source === "new_reviews") {
    return "aktuell";
  }
  if (source === "archive") {
    return "entdecken";
  }
  return null;
}

function toSavedAlbum(item: ApiSavedAlbum): SavedAlbum {
  return {
    reviewId: item.review_id,
    artist: item.artist,
    album: item.album,
    reviewUrl: item.review_url,
    source: apiSourceToRecommendationSource(item.source),
    savedAt: item.saved_at,
  };
}

export type { PlaylistExportResult } from "./playlistExport";
export { buildPlaylistExportPayload } from "./playlistExport";

/** Generates a synchronous playlist export from the API. */
export async function exportPlaylist(
  client: ApiClient,
  options: PlaylistExportRequestOptions,
): Promise<PlaylistExportResult> {
  return client.post<PlaylistExportResult>(
    "/v1/playlists/export",
    buildPlaylistExportPayload(options),
  );
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
    recommendations: response.items.map((item) => toRecommendation(item, "entdecken")),
    total: response.total,
  };
}

/** Loads one page of newest-review recommendations for a taste profile. */
export async function loadNewReviewRecommendations(
  client: ApiClient,
  profile: TemporaryTasteProfile | null,
  page: NewReviewsPageRequest = {},
): Promise<{ recommendations: Recommendation[]; total: number }> {
  const limit = page.limit ?? ARCHIVE_PAGE_SIZE;
  const offset = page.offset ?? 0;
  const newestCount = page.newestCount ?? 120;
  const payload: Record<string, unknown> = {
    limit,
    offset,
    newest_count: newestCount,
  };
  if (profile !== null) {
    payload.profile = temporaryProfileToApi(profile);
  }
  const response = await client.post<ApiRecommendationSet>(
    "/v1/recommendations/new-reviews",
    payload,
  );
  return {
    recommendations: response.items.map((item) => toRecommendation(item, "aktuell")),
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
  communityWeightsRaw: Record<string, number> = {},
): TemporaryTasteProfile {
  return {
    name: "Temporäres Musikprofil",
    selected_communities: selectedCommunities,
    community_weights_raw: migrateLegacyCommunityWeights(
      Object.fromEntries(
        selectedCommunities.map((communityId) => [
          communityId,
          communityWeightsRaw[communityId] ?? DEFAULT_COMMUNITY_WEIGHT_RAW,
        ]),
      ),
    ),
    filter_settings: normalizeFilterSettings(filterSettings),
  };
}

/** Normalizes partial or legacy filter settings to the supported API shape. */
export function normalizeFilterSettings(
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

function toRecommendation(
  item: ApiRecommendation,
  source: Recommendation["source"],
): Recommendation {
  const tags = item.matched_tags.map(toRecommendationTag);
  const fitPercent = Math.round(item.overall_score * 100);
  return {
    rank: item.rank,
    reviewId: item.review_id,
    artist: item.artist,
    album: item.album,
    year: item.year ?? 0,
    rating: item.rating ?? 0,
    score: item.overall_score,
    fitLabel: fitLabel(item.overall_score),
    fitPercent,
    releaseDate: item.release_date ?? undefined,
    recordLabel: item.labels || undefined,
    excerpt: item.text_excerpt,
    excerptContinues: item.text_excerpt_continues ?? false,
    reviewUrl: item.url ?? "https://www.plattentests.de/",
    tags,
    source,
    artistMbid: item.artist_mbid ?? undefined,
  };
}

function toRecommendationTag(tag: ApiCommunityMatch): RecommendationTag {
  return {
    label: tag.label,
    affinity: tag.affinity,
    matchesProfile: tag.matched,
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
