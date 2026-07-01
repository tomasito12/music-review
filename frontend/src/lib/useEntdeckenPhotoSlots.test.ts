// @vitest-environment jsdom

import { createElement, type ReactNode } from "react";
import { renderHook, waitFor } from "@testing-library/react";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

import type { Recommendation } from "../types";
import { ApiClientProvider } from "./apiClientContext";
import { useEntdeckenPhotoSlots } from "./useEntdeckenPhotoSlots";

const { loadArtistImagesBatchMock } = vi.hoisted(() => ({
  loadArtistImagesBatchMock: vi.fn(),
}));

vi.mock("./artistImageApi", () => ({
  loadArtistImagesBatch: loadArtistImagesBatchMock,
}));

function recommendation(rank: number): Recommendation {
  return {
    rank,
    reviewId: rank,
    artist: `Artist ${rank}`,
    album: `Album ${rank}`,
    year: 2024,
    rating: 8,
    score: 0.8,
    styleFit: 0.8,
    albumStyleBreadth: 0.5,
    fitLabel: "Passend",
    fitPercent: 80,
    excerpt: `Excerpt ${rank}`,
    reviewUrl: `https://example.com/${rank}`,
    tags: [],
    source: "entdecken",
    artistMbid: `mbid-${rank}`,
  };
}

function renderPhotoSlots(
  recommendations: Recommendation[],
  excludedArtistLookupKeys: ReadonlySet<string> = new Set(),
) {
  return renderHook(
    () => useEntdeckenPhotoSlots(recommendations, excludedArtistLookupKeys),
    {
      wrapper: ({ children }: { children: ReactNode }) =>
        createElement(ApiClientProvider, null, children),
    },
  );
}

describe("useEntdeckenPhotoSlots", () => {
  beforeEach(() => {
    loadArtistImagesBatchMock.mockImplementation(
      async (_client, artists: Array<{ artistMbid?: string; artistName?: string }>) => {
        const results = new Map<string, { thumbnailUrl: string }>();
        for (const artist of artists) {
          const lookupKey = artist.artistMbid?.trim() ?? "";
          if (lookupKey.length > 0) {
            results.set(lookupKey, {
              thumbnailUrl: `https://example.com/${lookupKey}.jpg`,
            });
          }
        }
        return results;
      },
    );
  });

  afterEach(() => {
    delete document.documentElement.dataset.visualTest;
    loadArtistImagesBatchMock.mockReset();
  });

  it("marks empty recommendation lists as settled immediately", () => {
    const { result } = renderPhotoSlots([]);

    expect(result.current.photoSlotsSettled).toBe(true);
    expect(result.current.photoRanks.size).toBe(0);
    expect(result.current.loadingPhotoRanks.size).toBe(0);
  });

  it("settles photo slots after the first resolution pass", async () => {
    const { result } = renderPhotoSlots([
      recommendation(1),
      recommendation(2),
      recommendation(3),
      recommendation(4),
      recommendation(5),
      recommendation(6),
    ]);

    await waitFor(() => {
      expect(result.current.photoSlotsSettled).toBe(true);
    });
    expect(result.current.loadingPhotoRanks.size).toBe(0);
    expect(result.current.photoRanks.has(1)).toBe(true);
  });

  it("defers progressive loading updates while visual-test mode is active", async () => {
    document.documentElement.dataset.visualTest = "true";
    const { result } = renderPhotoSlots([
      recommendation(1),
      recommendation(2),
      recommendation(3),
      recommendation(4),
      recommendation(5),
      recommendation(6),
    ]);

    await waitFor(() => {
      expect(result.current.photoSlotsSettled).toBe(true);
    });
    expect(result.current.loadingPhotoRanks.size).toBe(0);
    expect(result.current.photoRanks.has(1)).toBe(true);
  });
});
