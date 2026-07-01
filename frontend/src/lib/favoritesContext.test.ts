import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

import { mergeLocalFavoritesAfterLogin } from "./favoritesContext";
import {
  LOCAL_FAVORITES_STORAGE_KEY,
  addLocalFavorite,
  clearLocalFavorites,
} from "./localFavoritesStorage";
import { mergeFavorites } from "./plattenradarApi";
import {
  REMOVED_FAVORITES_STORAGE_KEY,
  addRemovedFavoriteId,
} from "./removedFavoritesStorage";

vi.mock("./plattenradarApi", () => ({
  mergeFavorites: vi.fn(),
  recommendationSourceToApiSource: vi.fn(() => "archive"),
}));

const mockedMergeFavorites = vi.mocked(mergeFavorites);

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
  clearLocalFavorites();
  window.localStorage.removeItem(REMOVED_FAVORITES_STORAGE_KEY);
  mockedMergeFavorites.mockReset();
  vi.unstubAllGlobals();
});

describe("mergeLocalFavoritesAfterLogin", () => {
  it("skips albums the user explicitly removed while signed in", async () => {
    mockedMergeFavorites.mockResolvedValue(0);
    addLocalFavorite({
      rank: 1,
      reviewId: 42,
      artist: "Alpha",
      album: "First",
      year: 2024,
      rating: 8,
      score: 0.8,
      fitLabel: "Passend",
      fitPercent: 80,
      styleFit: 0.8,
      albumStyleBreadth: 0.5,
      excerpt: "Excerpt",
      reviewUrl: "https://example.com/42",
      tags: [],
      source: "entdecken",
    });
    addRemovedFavoriteId(42);

    const client = {} as never;

    await expect(mergeLocalFavoritesAfterLogin(client)).resolves.toBe(0);
    expect(mockedMergeFavorites).not.toHaveBeenCalled();
    expect(window.localStorage.getItem(LOCAL_FAVORITES_STORAGE_KEY)).not.toBeNull();
  });
});
