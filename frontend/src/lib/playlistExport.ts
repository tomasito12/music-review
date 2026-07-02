import type { RecommendationSource } from "../types";
import type { TemporaryTasteProfile } from "./plattenradarApi";
import { temporaryProfileToApi } from "./plattenradarApi";

export type PlaylistApiSource = "archive" | "new_reviews";
export type PlaylistSelectionStrategy = "stratified" | "weighted_sample";

export interface PlaylistExportRequestOptions {
  archiveAlbumLimit: number;
  archiveDepth: number;
  format: "txt" | "csv";
  name: string;
  newestTasteFocus: number;
  profile: TemporaryTasteProfile;
  source: RecommendationSource;
  targetCount: number;
  updateRounds: string;
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

/** Map newest-playlist taste slider to API weighting parameters. */
export function tasteSettingsForNewest(tasteFocus: number): {
  selectionStrategy: PlaylistSelectionStrategy;
  tasteExponent: number;
} {
  const clamped = Math.min(1, Math.max(0, tasteFocus));
  return {
    tasteExponent: 1 + clamped * 2,
    selectionStrategy: clamped < 0.5 ? "stratified" : "weighted_sample",
  };
}

/** Map archive depth slider to API weighting parameters. */
export function tasteSettingsForArchive(depth: number): {
  selectionStrategy: PlaylistSelectionStrategy;
  tasteExponent: number;
} {
  const clamped = Math.min(1, Math.max(0, depth));
  return {
    tasteExponent: 1 + clamped * 2,
    selectionStrategy: clamped < 0.5 ? "weighted_sample" : "stratified",
  };
}

/** Builds the JSON body for POST /v1/playlists/export. */
export function buildPlaylistExportPayload(
  options: PlaylistExportRequestOptions,
): Record<string, unknown> {
  const apiSource = playlistApiSource(options.source);
  const taste =
    options.source === "entdecken"
      ? tasteSettingsForArchive(options.archiveDepth)
      : tasteSettingsForNewest(options.newestTasteFocus);

  return {
    source: apiSource,
    profile: temporaryProfileToApi(options.profile),
    playlist_name: options.name.trim() || defaultPlaylistName(),
    target_count: options.targetCount,
    taste_exponent: taste.tasteExponent,
    selection_strategy: taste.selectionStrategy,
    format: options.format,
    update_rounds: Number(options.updateRounds),
    archive_limit:
      options.source === "entdecken" ? Math.max(1, options.archiveAlbumLimit) : 200,
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
