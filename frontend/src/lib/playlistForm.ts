import { NEW_REVIEWS_PER_ROUND } from "./aktuellPage";
import type { RecommendationSource } from "../types";

export const PLAYLIST_TRACK_PRESETS = [20, 30, 50] as const;
export const PLAYLIST_TRACK_MIN = 5;
export const PLAYLIST_TRACK_MAX = 100;
export const PLAYLIST_DEFAULT_TRACK_COUNT = 30;

export const ARCHIVE_POOL_CHIP_VALUES = [50, 200] as const;

/** Supported update-round counts for playlist generation (matches API max 20). */
export const PLAYLIST_UPDATE_ROUND_VALUES = [1, 2, 4, 8, 12, 20] as const;

export type PlaylistUpdateRoundValue = (typeof PLAYLIST_UPDATE_ROUND_VALUES)[number];

/** Human-readable label for one update-round chip value. */
export function playlistUpdateRoundLabel(rounds: number): string {
  if (rounds === 1) {
    return "Letzte Runde";
  }
  return `Letzte ${rounds}`;
}

export const PLAYLIST_UPDATE_ROUND_OPTIONS = PLAYLIST_UPDATE_ROUND_VALUES.map((rounds) => ({
  value: String(rounds),
  label: playlistUpdateRoundLabel(rounds),
}));

export type NewestMoodPreset = "variety" | "balanced" | "focused";

export const NEWEST_MOOD_PRESETS: ReadonlyArray<{
  hint: string;
  id: NewestMoodPreset;
  label: string;
  tasteFocus: number;
}> = [
  {
    id: "variety",
    label: "Vielfalt",
    hint: "Breite Streuung, mehr Überraschungen.",
    tasteFocus: 0,
  },
  {
    id: "balanced",
    label: "Ausgewogen",
    hint: "Mix aus Bekanntem und Entdeckungen.",
    tasteFocus: 0.25,
  },
  {
    id: "focused",
    label: "Stark fokussiert",
    hint: "Nah an deinem Musikprofil.",
    tasteFocus: 1,
  },
];

export const DEFAULT_NEWEST_MOOD_PRESET: NewestMoodPreset = "balanced";

/** Maximum archive pool size accepted by POST /v1/playlists/export. */
export const PLAYLIST_ARCHIVE_LIMIT_MAX = 1000;

/** Highest selectable top-N album count for one archive playlist. */
export function archiveAlbumLimitCap(poolSize: number): number {
  if (poolSize <= 0) {
    return 0;
  }
  return Math.min(poolSize, PLAYLIST_ARCHIVE_LIMIT_MAX);
}

/** Lower and upper bounds for the archive top-N slider. */
export function archiveAlbumLimitBounds(poolSize: number): { max: number; min: number } {
  const max = archiveAlbumLimitCap(poolSize);
  if (max <= 0) {
    return { min: 0, max: 0 };
  }
  if (max < 20) {
    return { min: 1, max };
  }
  return { min: 20, max };
}

/** Default top-N album count for a personalized archive pool. */
export function defaultArchiveAlbumLimit(poolSize: number): number {
  if (poolSize <= 0) {
    return 0;
  }
  return Math.min(200, archiveAlbumLimitCap(poolSize));
}

/** Clamp a top-N album selection into the valid pool range. */
export function clampArchiveAlbumLimit(poolSize: number, value: number): number {
  const { min, max } = archiveAlbumLimitBounds(poolSize);
  if (max <= 0) {
    return 0;
  }
  return Math.min(max, Math.max(min, Math.round(value)));
}

/** Resolve quick-pick chip values for the archive pool control. */
export function archivePoolChipLimits(poolSize: number): number[] {
  const { max } = archiveAlbumLimitBounds(poolSize);
  if (max <= 0) {
    return [];
  }
  const chips = ARCHIVE_POOL_CHIP_VALUES.filter((value) => value < max);
  return [...chips, max];
}

/** Snap an update-round string to the nearest supported playlist value. */
export function normalizePlaylistUpdateRounds(value: string): string {
  const numeric = Number(value);
  if (PLAYLIST_UPDATE_ROUND_VALUES.includes(numeric as PlaylistUpdateRoundValue)) {
    return String(numeric);
  }
  if (Number.isNaN(numeric) || numeric <= 1) {
    return "1";
  }
  const nearest = PLAYLIST_UPDATE_ROUND_VALUES.reduce((best, candidate) =>
    Math.abs(candidate - numeric) < Math.abs(best - numeric) ? candidate : best,
  );
  return String(nearest);
}

/** Map a newest mood preset to the legacy taste-focus slider value. */
export function newestMoodToTasteFocus(preset: NewestMoodPreset): number {
  const match = NEWEST_MOOD_PRESETS.find((entry) => entry.id === preset);
  return match?.tasteFocus ?? NEWEST_MOOD_PRESETS[1].tasteFocus;
}

/** Helper copy under the newest mood preset chips. */
export function newestMoodHint(preset: NewestMoodPreset): string {
  const match = NEWEST_MOOD_PRESETS.find((entry) => entry.id === preset);
  return match?.hint ?? "";
}

/** Estimated review pool size for the selected update-round window. */
export function playlistUpdateRoundPoolHint(updateRounds: string): string {
  const rounds = Number(normalizePlaylistUpdateRounds(updateRounds));
  const estimated = Math.min(200, rounds * NEW_REVIEWS_PER_ROUND);
  return `~${estimated} Reviews (geschätzt, je ~${NEW_REVIEWS_PER_ROUND} pro Runde).`;
}

/** Human-readable archive pool summary for the form. */
export function archivePoolSummary(poolSize: number, albumLimit: number): string {
  if (poolSize <= 0) {
    return "Keine passenden Alben für dein Profil gefunden.";
  }
  const cap = archiveAlbumLimitCap(poolSize);
  const effectiveLimit = Math.min(albumLimit, cap);
  if (effectiveLimit >= cap && poolSize <= PLAYLIST_ARCHIVE_LIMIT_MAX) {
    return `${poolSize} Alben passen zu deinem Profil — Playlist aus allen.`;
  }
  return `${poolSize} Alben passen zu deinem Profil — Playlist aus den Top ${effectiveLimit}.`;
}

/** Clamp playlist track count into the supported range. */
export function clampTrackCount(value: number): number {
  return Math.min(PLAYLIST_TRACK_MAX, Math.max(PLAYLIST_TRACK_MIN, Math.round(value)));
}

/** Short helper copy under the track-count presets. */
export function trackCountHint(count: number): string {
  if (count >= 50) {
    return `${count} Titel — längere Hörsession`;
  }
  if (count >= 30) {
    return `${count} Titel — gut zum Reinhören`;
  }
  return `${count} Titel — kompakte Auswahl`;
}

/** Context line when opening playlists from Aktuell or Entdecken. */
export function playlistSourceContextLine(
  source: RecommendationSource,
  updateRounds: string,
): string {
  if (source === "entdecken") {
    return "Aus dem Plattentests-Archiv";
  }
  const label =
    PLAYLIST_UPDATE_ROUND_OPTIONS.find((option) => option.value === updateRounds)?.label ??
    playlistUpdateRoundLabel(Number(normalizePlaylistUpdateRounds(updateRounds)));
  return `Aus deinen Neuheiten · ${label}`;
}

/** Label for one archive pool quick-pick chip. */
export function archivePoolChipLabel(
  chipValue: number,
  poolSize: number,
  boundsMax: number,
): string {
  if (chipValue >= boundsMax) {
    if (poolSize > PLAYLIST_ARCHIVE_LIMIT_MAX) {
      return "Bis 1000";
    }
    return "Alle";
  }
  return String(chipValue);
}

/** Success headline shown after playlist generation. */
export function playlistSuccessHeadline(
  source: RecommendationSource,
  itemCount: number,
): string {
  const sourceLabel = source === "entdecken" ? "dem Archiv" : "deinen Neuheiten";
  return `Deine Playlist ist fertig — ${itemCount} Titel aus ${sourceLabel}.`;
}
