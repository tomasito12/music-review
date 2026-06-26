import { describe, expect, it } from "vitest";

import {
  buildAktuellHighlights,
  buildAktuellSummary,
  newestCountFromUpdateRounds,
} from "./aktuellPage";
import type { Recommendation } from "../types";

const sampleRecommendations: Recommendation[] = [
  {
    rank: 1,
    artist: "Alpha",
    album: "First",
    year: 2024,
    rating: 8,
    score: 0.9,
    fitLabel: "Sehr passend",
    fitPercent: 90,
    excerpt: "A",
    reviewUrl: "https://example.com/a",
    tags: [{ label: "Indie", strength: "high", matchesProfile: true }],
    source: "aktuell",
  },
  {
    rank: 2,
    artist: "Beta",
    album: "Second",
    year: 2024,
    rating: 9,
    score: 0.5,
    fitLabel: "Passend",
    fitPercent: 50,
    excerpt: "B",
    reviewUrl: "https://example.com/b",
    tags: [{ label: "Jazz", strength: "medium", matchesProfile: false }],
    source: "aktuell",
  },
];

describe("newestCountFromUpdateRounds", () => {
  it("scales update rounds into API newest_count values", () => {
    expect(newestCountFromUpdateRounds(1)).toBe(30);
    expect(newestCountFromUpdateRounds(4)).toBe(120);
    expect(newestCountFromUpdateRounds(8)).toBe(200);
  });
});

describe("buildAktuellSummary", () => {
  it("returns an empty-state summary when no reviews are available", () => {
    expect(buildAktuellSummary(0).title).toContain("Noch keine");
  });
});

describe("buildAktuellHighlights", () => {
  it("builds three highlight cards from ranked recommendations", () => {
    const highlights = buildAktuellHighlights(sampleRecommendations);

    expect(highlights.length).toBeGreaterThanOrEqual(2);
    expect(highlights[0]?.label).toBe("Beste Passung");
    expect(highlights[0]?.recommendation.artist).toBe("Alpha");
    expect(highlights[1]?.recommendation.artist).toBe("Beta");
  });
});
