import type { RecommendationSource } from "../types";
import type { TemporaryTasteProfile } from "./plattenradarApi";
import { newestCountFromUpdateRounds } from "./aktuellPage";
import { temporaryProfileToApi } from "./plattenradarApi";

export type PlaylistApiSource = "archive" | "new_reviews";
export type PlaylistSelectionStrategy = "stratified" | "weighted_sample";

export interface PlaylistExportRequestOptions {
  format: "txt" | "csv";
  focus: "balanced" | "top";
  name: string;
  profile: TemporaryTasteProfile;
  source: RecommendationSource;
  targetCount: number;
  updateRounds: string;
  variation: number;
}

export interface PlaylistExportItem {
  album: string;
  artist: string;
  raw_score: number;
  review_id: number;
  score_weight: number;
  source_kind: string;
  track_title: string;
}

export interface PlaylistExportResult {
  content: string;
  content_type: string;
  filename: string;
  format: "txt" | "csv";
  items: PlaylistExportItem[];
  name: string;
  source: PlaylistApiSource;
}

/** Maps UI recommendation sources to API playlist sources. */
export function playlistApiSource(source: RecommendationSource): PlaylistApiSource {
  return source === "entdecken" ? "archive" : "new_reviews";
}

/** Maps UI focus and source to the API selection strategy. */
export function playlistSelectionStrategy(
  source: RecommendationSource,
  focus: "balanced" | "top",
): PlaylistSelectionStrategy {
  if (focus === "top") {
    return "weighted_sample";
  }
  return source === "entdecken" ? "weighted_sample" : "stratified";
}

/** Maps UI focus and variation to the API taste exponent. */
export function playlistTasteExponent(
  focus: "balanced" | "top",
  variation: number,
): number {
  if (focus === "top") {
    return 3;
  }
  return 1 + Math.min(1, Math.max(0, variation)) * 2;
}

/** Builds the JSON body for POST /v1/playlists/export. */
export function buildPlaylistExportPayload(
  options: PlaylistExportRequestOptions,
): Record<string, unknown> {
  const apiSource = playlistApiSource(options.source);
  return {
    source: apiSource,
    profile: temporaryProfileToApi(options.profile),
    playlist_name: options.name.trim() || defaultPlaylistName(),
    target_count: options.targetCount,
    taste_exponent: playlistTasteExponent(options.focus, options.variation),
    selection_strategy: playlistSelectionStrategy(options.source, options.focus),
    format: options.format,
    newest_count:
      apiSource === "new_reviews"
        ? newestCountFromUpdateRounds(Number(options.updateRounds))
        : 20,
    archive_limit: 200,
  };
}

/** Returns a default playlist name with the current date. */
export function defaultPlaylistName(date = new Date()): string {
  return `Plattenradar ${date.toISOString().slice(0, 10)}`;
}

/** Builds a CSV export from playlist items when only TXT was requested from the API. */
export function playlistItemsToCsv(items: PlaylistExportItem[]): string {
  const header = "Artist,Album,Track";
  const rows = items.map((item) =>
    [item.artist, item.album, item.track_title].map(escapeCsvField).join(","),
  );
  return [header, ...rows].join("\n");
}

/** Triggers a browser download for generated playlist export content. */
export function downloadPlaylistContent(
  filename: string,
  content: string,
  contentType: string,
): void {
  const blob = new Blob([content], { type: contentType });
  const url = URL.createObjectURL(blob);
  const anchor = document.createElement("a");
  anchor.href = url;
  anchor.download = filename;
  anchor.click();
  URL.revokeObjectURL(url);
}

function escapeCsvField(value: string): string {
  if (value.includes(",") || value.includes('"') || value.includes("\n")) {
    return `"${value.replaceAll('"', '""')}"`;
  }
  return value;
}
