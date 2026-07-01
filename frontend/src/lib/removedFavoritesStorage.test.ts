import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

import {
  REMOVED_FAVORITES_STORAGE_KEY,
  addRemovedFavoriteId,
  readRemovedFavoriteIds,
  removeRemovedFavoriteId,
} from "./removedFavoritesStorage";

function installStorageMock(): void {
  const localStore = new Map<string, string>();
  vi.stubGlobal("window", {
    localStorage: {
      getItem: (key: string) => localStore.get(key) ?? null,
      setItem: (key: string, value: string) => {
        localStore.set(key, value);
      },
      removeItem: (key: string) => {
        localStore.delete(key);
      },
    },
  });
}

beforeEach(() => {
  installStorageMock();
});

afterEach(() => {
  window.localStorage.removeItem(REMOVED_FAVORITES_STORAGE_KEY);
  vi.unstubAllGlobals();
});

describe("removedFavoritesStorage", () => {
  it("ignores malformed payloads", () => {
    window.localStorage.setItem(
      REMOVED_FAVORITES_STORAGE_KEY,
      JSON.stringify({ reviewIds: ["bad"] }),
    );

    expect(readRemovedFavoriteIds()).toEqual(new Set());
  });

  it("stores multiple removed IDs in sorted order", () => {
    addRemovedFavoriteId(99);
    addRemovedFavoriteId(12);

    expect(readRemovedFavoriteIds()).toEqual(new Set([12, 99]));
    expect(
      JSON.parse(window.localStorage.getItem(REMOVED_FAVORITES_STORAGE_KEY) ?? "{}"),
    ).toEqual({ reviewIds: [12, 99] });
  });

  it("does nothing when clearing an unknown ID", () => {
    addRemovedFavoriteId(7);
    removeRemovedFavoriteId(8);

    expect(readRemovedFavoriteIds()).toEqual(new Set([7]));
  });
});
