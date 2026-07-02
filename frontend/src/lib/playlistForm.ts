import { UPDATE_ROUND_OPTIONS } from "./aktuellPage";
import type { RecommendationSource } from "../types";

export const PLAYLIST_TRACK_PRESETS = [20, 30, 50] as const;
export const PLAYLIST_TRACK_MIN = 5;
export const PLAYLIST_TRACK_MAX = 100;
export const PLAYLIST_DEFAULT_TRACK_COUNT = 30;

export const ARCHIVE_POOL_CHIP_VALUES = [50, 200] as const;

/** Lower and upper bounds for the archive top-N slider. */
export function archiveAlbumLimitBounds(poolSize: number): { max: number; min: number } {
  if (poolSize <= 0) {
    return { min: 0, max: 0 };
  }
  if (poolSize < 20) {
    return { min: 1, max: poolSize };
  }
  return { min: 20, max: poolSize };
}

/** Default top-N album count for a personalized archive pool. */
export function defaultArchiveAlbumLimit(poolSize: number): number {
  if (poolSize <= 0) {
    return 0;
  }
  return Math.min(200, poolSize);
}

/** Clamp a top-N album selection into the valid pool range. */
export function clampArchiveAlbumLimit(poolSize: number, value: number): number {
  const { min, max } = archiveAlbumLimitBounds(poolSize);
  if (max <= 0) {
    return 0;
  }
  return Math.min(max, Math.max(min, Math.round(value)));
}

/** Resolve quick-pick chip values for the archive pool slider. */
export function archivePoolChipLimits(poolSize: number): number[] {
  const { max } = archiveAlbumLimitBounds(poolSize);
  if (max <= 0) {
    return [];
  }
  const chips = ARCHIVE_POOL_CHIP_VALUES.filter((value) => value < max);
  return [...chips, max];
}

/** Human-readable archive pool summary for the form. */
export function archivePoolSummary(poolSize: number, albumLimit: number): string {
  if (poolSize <= 0) {
    return "Keine passenden Alben für dein Profil gefunden.";
  }
  if (albumLimit >= poolSize) {
    return `${poolSize} Alben passen zu deinem Profil — Playlist aus allen.`;
  }
  return `${poolSize} Alben passen zu deinem Profil — Playlist aus den Top ${albumLimit}.`;
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
    UPDATE_ROUND_OPTIONS.find((option) => option.value === updateRounds)?.label ??
    "gewählter Zeitraum";
  return `Aus deinen Neuheiten · ${label}`;
}
