import { describe, expect, it } from "vitest";

import {
  buildAktuellBriefing,
  buildAktuellHighlights,
  buildAktuellSummary,
  newestCountFromUpdateRounds,
} from "./aktuellPage";
import type { Recommendation } from "../types";

const sampleRecommendations: Recommendation[] = [
  {
    rank: 1,
    reviewId: 1,
    artist: "Alpha",
    album: "First",
    year: 2024,
    rating: 8,
    score: 0.9,
    styleFit: 0.9,
    albumStyleBreadth: 0.5,
    fitLabel: "Sehr passend",
    fitPercent: 90,
    excerpt: "A",
    reviewUrl: "https://example.com/a",
    tags: [{ label: "Indie", affinity: 0.8, matchesProfile: true }],
    source: "aktuell",
  },
  {
    rank: 2,
    reviewId: 2,
    artist: "Beta",
    album: "Second",
    year: 2024,
    rating: 9,
    score: 0.5,
    styleFit: 0.5,
    albumStyleBreadth: 0.3,
    fitLabel: "Passend",
    fitPercent: 50,
    excerpt: "B",
    reviewUrl: "https://example.com/b",
    tags: [{ label: "Jazz", affinity: 0.4, matchesProfile: false }],
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

  it("frames non-empty updates as listening entry points", () => {
    expect(buildAktuellSummary(6).title).toBe(
      "Drei Einstiege für deinen ersten Klick.",
    );
  });
});

describe("buildAktuellBriefing", () => {
  it("frames an empty update without implying personal matches", () => {
    const briefing = buildAktuellBriefing(0, 0, "Letzte Update-Runde");

    expect(briefing.title).toContain("keine sicheren Treffer");
  });

  it("uses a more exploratory tone for small update batches", () => {
    const briefing = buildAktuellBriefing(2, 2, "Letzte 4 Update-Runden");

    expect(briefing.title).toContain("kleiner Schwung");
  });

  it("welcomes returning listeners for larger batches", () => {
    const briefing = buildAktuellBriefing(12, 5, "Letzte 8 Update-Runden");

    expect(briefing.kicker).toBe("Schön, dass du zurück bist");
  });

  it("uses shown count when API total is temporarily zero", () => {
    const briefing = buildAktuellBriefing(0, 8, "Letzte 4 Update-Runden");

    expect(briefing.title).toContain("8 neue Rezensionen");
    expect(briefing.title).not.toContain("keine sicheren Treffer");
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
