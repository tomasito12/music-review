import { describe, expect, it } from "vitest";

import {
  shouldShowResultsListPrelude,
  shouldShowStandaloneFilterRegion,
} from "./resultsListLayout";

describe("shouldShowResultsListPrelude", () => {
  it("shows the prelude only when editorial highlights exist", () => {
    expect(shouldShowResultsListPrelude([])).toBe(false);
    expect(
      shouldShowResultsListPrelude([
        {
          label: "Beste Gesamtpassung",
          description: "Top pick",
          recommendation: {
            rank: 1,
            reviewId: 1,
            artist: "Alpha",
            album: "First",
            year: 2024,
            rating: 8,
            score: 0.9,
            styleFit: 0.9,
            albumStyleBreadth: 0.4,
            fitLabel: "Passend",
            fitPercent: 90,
            excerpt: "Excerpt",
            reviewUrl: "https://example.com/1",
            tags: [],
            source: "entdecken",
          },
        },
      ]),
    ).toBe(true);
  });
});

describe("shouldShowStandaloneFilterRegion", () => {
  it("renders filters without the prelude when highlights are missing", () => {
    expect(shouldShowStandaloneFilterRegion(true, false)).toBe(true);
    expect(shouldShowStandaloneFilterRegion(true, true)).toBe(false);
    expect(shouldShowStandaloneFilterRegion(false, false)).toBe(false);
  });
});
