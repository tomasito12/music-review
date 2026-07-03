import type { RecommendationSource } from "../types";
import { PLAYLIST_ARCHIVE_LIMIT_MAX } from "./playlistForm";
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
  artist_mbid?: string | null;
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
      options.source === "entdecken"
        ? Math.min(
            PLAYLIST_ARCHIVE_LIMIT_MAX,
            Math.max(1, options.archiveAlbumLimit),
          )
        : 200,
  };
}

/** Returns a mode-specific default playlist name with the current date. */
export function defaultPlaylistNameForSource(
  source: RecommendationSource,
  date = isVisualTestMode() ? VISUAL_TEST_REFERENCE_DATE : new Date(),
): string {
  const datePart = date.toISOString().slice(0, 10);
  if (source === "entdecken") {
    return `Platten-Archiv ${datePart}`;
  }
  return `Plattenradar ${datePart}`;
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

/** Remove a trailing numeric export suffix such as ``(2)``. */
export function stripPlaylistNameSuffix(name: string): string {
  const trimmed = name.trim();
  const match = PLAYLIST_NAME_SUFFIX_RE.exec(trimmed);
  if (match !== null) {
    return (match[1] ?? trimmed).trim();
  }
  return trimmed;
}

/** Build the playlist name for one export download (1 = base name, 2+ adds suffix). */
export function playlistNameForExportDownload(
  baseName: string,
  downloadNumber: number,
): string {
  const base = stripPlaylistNameSuffix(baseName) || defaultPlaylistName();
  let result = base;
  for (let index = 1; index < downloadNumber; index += 1) {
    result = bumpPlaylistNameSuffix(result);
  }
  return result;
}

function csvCell(value: string): string {
  if (/[",\n\r]/.test(value)) {
    return `"${value.replace(/"/g, '""')}"`;
  }
  return value;
}

/** Builds TuneMyMusic CSV from playlist items and a playlist title. */
export function playlistItemsToCsv(
  items: PlaylistExportItem[],
  playlistName: string,
): string {
  const name = playlistName.trim() || defaultPlaylistName();
  const rows = [
    "Track name,Artist name,Playlist name",
    ...playlistItemsToTxtRows(items).map(
      ([artist, title]) =>
        `${csvCell(title)},${csvCell(artist)},${csvCell(name)}`,
    ),
  ];
  return rows.join("\n");
}

function playlistItemsToTxtRows(
  items: PlaylistExportItem[],
): Array<[string, string]> {
  const seen = new Set<string>();
  const rows: Array<[string, string]> = [];

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
    rows.push([artist, title]);
  }

  return rows;
}

/** Build a safe local filename for one playlist export download. */
export function suggestedPlaylistExportFilename(
  playlistName: string,
  extension: ".csv" | ".txt" = ".csv",
): string {
  let base = playlistName.trim() || "plattenradar";
  base = base.replace(/[<>:"/\\|?*\u0000-\u001f]/g, "");
  base = base.replace(/\s+/g, "-").replace(/^[-._]+|[-._]+$/g, "");
  if (!base) {
    base = "plattenradar";
  }
  return `${base}${extension}`;
}

/** Builds TuneMyMusic free-text lines from playlist items. */
export function playlistItemsToTxt(items: PlaylistExportItem[]): string {
  return playlistItemsToTxtRows(items)
    .map(([artist, title]) => `${artist} - ${title}`)
    .join("\n");
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
