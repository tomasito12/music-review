// @vitest-environment jsdom

import { afterEach, describe, expect, it } from "vitest";

import type { Recommendation } from "../types";
import {
  limitRecommendationsForVisualTest,
  shouldShowLoadMoreButton,
  VISUAL_TEST_LIST_ITEM_LIMIT,
} from "./visualTestListLimit";

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
  };
}

describe("limitRecommendationsForVisualTest", () => {
  afterEach(() => {
    delete document.documentElement.dataset.visualTest;
  });

  it("returns the full list outside visual-test mode", () => {
    const recommendations = Array.from({ length: 12 }, (_, index) =>
      recommendation(index + 1),
    );

    expect(limitRecommendationsForVisualTest(recommendations)).toHaveLength(12);
  });

  it("limits long lists while visual-test mode is active", () => {
    document.documentElement.dataset.visualTest = "true";
    const recommendations = Array.from({ length: 12 }, (_, index) =>
      recommendation(index + 1),
    );

    expect(limitRecommendationsForVisualTest(recommendations)).toHaveLength(
      VISUAL_TEST_LIST_ITEM_LIMIT,
    );
  });
});

describe("shouldShowLoadMoreButton", () => {
  afterEach(() => {
    delete document.documentElement.dataset.visualTest;
  });

  it("shows load more when more items are available outside visual-test mode", () => {
    expect(shouldShowLoadMoreButton(true)).toBe(true);
  });

  it("hides load more when no further items are available", () => {
    expect(shouldShowLoadMoreButton(false)).toBe(false);
  });

  it("hides load more during visual regression runs", () => {
    document.documentElement.dataset.visualTest = "true";

    expect(shouldShowLoadMoreButton(true)).toBe(false);
  });
});
