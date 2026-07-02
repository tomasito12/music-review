import type { RecommendationSource } from "../types";
import type { TemporaryTasteProfile } from "./plattenradarApi";
import { temporaryProfileToApi } from "./plattenradarApi";
import { isVisualTestMode } from "./visualTestMode";

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

const PLAYLIST_NAME_SUFFIX_RE = /^(.*) \((\d+)\)$/;
const VISUAL_TEST_REFERENCE_DATE = new Date("2026-06-27T12:00:00.000Z");

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
    playlist_name:
      options.name.trim() || defaultPlaylistNameForSource(options.source),
    target_count: options.targetCount,
    taste_exponent: taste.tasteExponent,
    selection_strategy: taste.selectionStrategy,
    format: options.format,
    update_rounds: Number(options.updateRounds),
    archive_limit:
      options.source === "entdecken" ? Math.max(1, options.archiveAlbumLimit) : 200,
  };
}

/** Returns a mode-specific default playlist name with the current date. */
export function defaultPlaylistNameForSource(
  source: RecommendationSource,
  date = isVisualTestMode() ? VISUAL_TEST_REFERENCE_DATE : new Date(),
): string {
  const datePart = date.toISOString().slice(0, 10);
  if (source === "entdecken") {
    return `Plattenradar Archiv ${datePart}`;
  }
  return `Plattenradar Neuheiten ${datePart}`;
}

/** Returns a default playlist name with the current date. */
export function defaultPlaylistName(date = new Date()): string {
  return defaultPlaylistNameForSource("aktuell", date);
}

/** Increments or appends a numeric remix suffix such as ``(2)``. */
export function bumpPlaylistNameSuffix(name: string): string {
  const trimmed = name.trim();
  if (!trimmed) {
    return defaultPlaylistName();
  }

  const match = PLAYLIST_NAME_SUFFIX_RE.exec(trimmed);
  if (match !== null) {
    const baseName = match[1] ?? trimmed;
    const nextSuffix = Number(match[2]) + 1;
    return `${baseName} (${nextSuffix})`;
  }

  return `${trimmed} (2)`;
}

/** Builds TuneMyMusic free-text lines from playlist items. */
export function playlistItemsToTxt(items: PlaylistExportItem[]): string {
  const seen = new Set<string>();
  const lines: string[] = [];

  for (const item of items) {
    const artist = item.artist.trim();
    const title = item.track_title.trim();
    if (!artist || !title) {
      continue;
    }

    const key = `${artist.toLowerCase()}\0${title.toLowerCase()}`;
    if (seen.has(key)) {
      continue;
    }
    seen.add(key);
    lines.push(`${artist} - ${title}`);
  }

  return lines.join("\n");
}

/** Derives a TXT filename from a CSV export filename. */
export function playlistTxtFilename(csvFilename: string): string {
  return csvFilename.replace(/\.csv$/i, ".txt");
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
