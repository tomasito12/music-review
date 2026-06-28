import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

import type { Recommendation } from "../types";

import {
  LOCAL_FAVORITES_STORAGE_KEY,
  addLocalFavorite,
  clearLocalFavorites,
  readLocalFavorites,
  removeLocalFavorite,
} from "./localFavoritesStorage";

function sampleRecommendation(reviewId: number): Recommendation {
  return {
    rank: 1,
    reviewId,
    artist: "Alpha",
    album: "First",
    year: 2024,
    rating: 8,
    score: 0.8,
    fitLabel: "Passend",
    fitPercent: 80,
    excerpt: "Excerpt",
    reviewUrl: `https://example.com/${reviewId}`,
    tags: [],
    source: "entdecken",
  };
}

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
  vi.unstubAllGlobals();
});

describe("localFavoritesStorage", () => {
  it("returns an empty list when nothing is stored", () => {
    expect(readLocalFavorites()).toEqual([]);
  });

  it("adds and removes one guest favorite", () => {
    addLocalFavorite(sampleRecommendation(42));
    expect(readLocalFavorites()).toHaveLength(1);
    expect(readLocalFavorites()[0]?.reviewId).toBe(42);

    removeLocalFavorite(42);
    expect(readLocalFavorites()).toEqual([]);
  });

  it("ignores malformed payloads", () => {
    window.localStorage.setItem(
      LOCAL_FAVORITES_STORAGE_KEY,
      JSON.stringify({ items: [{ reviewId: "bad" }] }),
    );

    expect(readLocalFavorites()).toEqual([]);
  });
});
