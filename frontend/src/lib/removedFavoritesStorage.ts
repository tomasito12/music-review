export const REMOVED_FAVORITES_STORAGE_KEY = "plattenradar.removed-server-favorites.v1";

interface RemovedFavoritesPayload {
  reviewIds: number[];
}

/** Reads review IDs the user explicitly removed while signed in. */
export function readRemovedFavoriteIds(): Set<number> {
  if (typeof window === "undefined") {
    return new Set();
  }
  const raw = window.localStorage.getItem(REMOVED_FAVORITES_STORAGE_KEY);
  if (raw === null) {
    return new Set();
  }
  try {
    const parsed: unknown = JSON.parse(raw);
    if (
      typeof parsed !== "object" ||
      parsed === null ||
      !Array.isArray((parsed as RemovedFavoritesPayload).reviewIds)
    ) {
      return new Set();
    }
    return new Set(
      (parsed as RemovedFavoritesPayload).reviewIds.filter(
        (value): value is number => typeof value === "number",
      ),
    );
  } catch {
    return new Set();
  }
}

function writeRemovedFavoriteIds(reviewIds: Set<number>): void {
  if (typeof window === "undefined") {
    return;
  }
  const payload: RemovedFavoritesPayload = {
    reviewIds: [...reviewIds].sort((left, right) => left - right),
  };
  if (payload.reviewIds.length === 0) {
    window.localStorage.removeItem(REMOVED_FAVORITES_STORAGE_KEY);
    return;
  }
  window.localStorage.setItem(REMOVED_FAVORITES_STORAGE_KEY, JSON.stringify(payload));
}

/** Remembers that a saved album must not be restored from guest storage. */
export function addRemovedFavoriteId(reviewId: number): void {
  const nextIds = readRemovedFavoriteIds();
  nextIds.add(reviewId);
  writeRemovedFavoriteIds(nextIds);
}

/** Clears a removal marker after the user saves the album again. */
export function removeRemovedFavoriteId(reviewId: number): void {
  const nextIds = readRemovedFavoriteIds();
  if (!nextIds.delete(reviewId)) {
    return;
  }
  writeRemovedFavoriteIds(nextIds);
}
