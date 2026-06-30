import type { Recommendation, RecommendationSource, SavedAlbum } from "../types";

import { removeRemovedFavoriteId } from "./removedFavoritesStorage";

export const LOCAL_FAVORITES_STORAGE_KEY = "plattenradar.local-favorites.v1";

export interface LocalFavorite {
  reviewId: number;
  artist: string;
  album: string;
  reviewUrl: string;
  source: RecommendationSource | null;
  savedAt: string;
}

interface LocalFavoritesPayload {
  items: LocalFavorite[];
}

function isLocalFavorite(value: unknown): value is LocalFavorite {
  if (typeof value !== "object" || value === null) {
    return false;
  }
  const candidate = value as LocalFavorite;
  return (
    typeof candidate.reviewId === "number" &&
    typeof candidate.artist === "string" &&
    typeof candidate.album === "string" &&
    typeof candidate.reviewUrl === "string" &&
    (candidate.source === null ||
      candidate.source === "aktuell" ||
      candidate.source === "entdecken") &&
    typeof candidate.savedAt === "string"
  );
}

/** Reads guest favorites from local storage. */
export function readLocalFavorites(): LocalFavorite[] {
  if (typeof window === "undefined") {
    return [];
  }
  const raw = window.localStorage.getItem(LOCAL_FAVORITES_STORAGE_KEY);
  if (raw === null) {
    return [];
  }
  try {
    const parsed: unknown = JSON.parse(raw);
    if (
      typeof parsed !== "object" ||
      parsed === null ||
      !Array.isArray((parsed as LocalFavoritesPayload).items)
    ) {
      return [];
    }
    return (parsed as LocalFavoritesPayload).items.filter(isLocalFavorite);
  } catch {
    return [];
  }
}

function writeLocalFavorites(items: LocalFavorite[]): void {
  if (typeof window === "undefined") {
    return;
  }
  const payload: LocalFavoritesPayload = { items };
  window.localStorage.setItem(LOCAL_FAVORITES_STORAGE_KEY, JSON.stringify(payload));
}

/** Adds or updates one guest favorite in local storage. */
export function addLocalFavorite(recommendation: Recommendation): LocalFavorite[] {
  removeRemovedFavoriteId(recommendation.reviewId);
  const savedAt = new Date().toISOString().replace(/\.\d{3}Z$/, "Z");
  const nextFavorite: LocalFavorite = {
    reviewId: recommendation.reviewId,
    artist: recommendation.artist,
    album: recommendation.album,
    reviewUrl: recommendation.reviewUrl,
    source: recommendation.source,
    savedAt,
  };
  const withoutCurrent = readLocalFavorites().filter(
    (item) => item.reviewId !== recommendation.reviewId,
  );
  const nextItems = [nextFavorite, ...withoutCurrent];
  writeLocalFavorites(nextItems);
  return nextItems;
}

/** Removes one guest favorite from local storage. */
export function removeLocalFavorite(reviewId: number): LocalFavorite[] {
  const nextItems = readLocalFavorites().filter((item) => item.reviewId !== reviewId);
  writeLocalFavorites(nextItems);
  return nextItems;
}

/** Clears all guest favorites from local storage. */
export function clearLocalFavorites(): void {
  if (typeof window === "undefined") {
    return;
  }
  window.localStorage.removeItem(LOCAL_FAVORITES_STORAGE_KEY);
}

/** Converts guest favorites into SavedAlbum rows for the account page. */
export function localFavoritesToSavedAlbums(items: LocalFavorite[]): SavedAlbum[] {
  return items.map((item) => ({
    reviewId: item.reviewId,
    artist: item.artist,
    album: item.album,
    reviewUrl: item.reviewUrl,
    source: item.source,
    savedAt: item.savedAt,
  }));
}
