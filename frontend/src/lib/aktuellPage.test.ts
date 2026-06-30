import { describe, expect, it } from "vitest";

import {
  OUTSIDE_PROFILE_SCORE_MAX,
  buildAktuellBriefing,
  buildAktuellHighlights,
  buildAktuellSummary,
  newestCountFromUpdateRounds,
} from "./aktuellPage";
import type { Recommendation } from "../types";

function recommendation(
  overrides: Partial<Recommendation> & Pick<Recommendation, "artist" | "album">,
): Recommendation {
  return {
    rank: 1,
    reviewId: 1,
    year: 2024,
    rating: 7,
    score: 0.5,
    styleFit: 0.5,
    albumStyleBreadth: 0.4,
    fitLabel: "Passend",
    fitPercent: 50,
    excerpt: "Excerpt",
    reviewUrl: "https://example.com",
    tags: [],
    source: "aktuell",
    ...overrides,
  };
}

const sampleRecommendations: Recommendation[] = [
  recommendation({
    reviewId: 1,
    artist: "Alpha",
    album: "First",
    rating: 8,
    score: 0.9,
    tags: [{ label: "Indie", affinity: 0.8, matchesProfile: true }],
  }),
  recommendation({
    reviewId: 2,
    artist: "Beta",
    album: "Second",
    rating: 9,
    score: 0.5,
    tags: [{ label: "Jazz", affinity: 0.4, matchesProfile: false }],
  }),
  recommendation({
    reviewId: 3,
    artist: "Gamma",
    album: "Third",
    rating: 8,
    score: 0.55,
    tags: [{ label: "Metal", affinity: 0.2, matchesProfile: false }],
  }),
];

describe("newestCountFromUpdateRounds", () => {
  it("scales update rounds into API newest_count values", () => {
    expect(newestCountFromUpdateRounds(1)).toBe(20);
    expect(newestCountFromUpdateRounds(4)).toBe(80);
    expect(newestCountFromUpdateRounds(8)).toBe(160);
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
  it("picks the highest overall score as Beste Passung", () => {
    const highlights = buildAktuellHighlights(sampleRecommendations);

    expect(highlights[0]?.label).toBe("Beste Passung");
    expect(highlights[0]?.recommendation.artist).toBe("Alpha");
  });

  it("picks the highest critic rating among remaining albums as Kritikerfavorit", () => {
    const highlights = buildAktuellHighlights(sampleRecommendations);

    expect(highlights[1]?.label).toBe("Kritikerfavorit");
    expect(highlights[1]?.recommendation.artist).toBe("Beta");
  });

  it("picks a low-fit but highly rated album outside the critic favorite", () => {
    const highlights = buildAktuellHighlights(sampleRecommendations);

    expect(highlights[2]?.label).toBe("Außerhalb deines Profils");
    expect(highlights[2]?.recommendation.artist).toBe("Gamma");
    expect(highlights[2]?.recommendation.score).toBeLessThan(
      OUTSIDE_PROFILE_SCORE_MAX,
    );
  });

  it("breaks critic-rating ties by overall score", () => {
    const highlights = buildAktuellHighlights([
      recommendation({
        artist: "Alpha",
        album: "First",
        rating: 8,
        score: 0.95,
      }),
      recommendation({
        artist: "Beta",
        album: "Second",
        rating: 9,
        score: 0.6,
      }),
      recommendation({
        artist: "Gamma",
        album: "Third",
        rating: 9,
        score: 0.65,
      }),
    ]);

    expect(highlights[1]?.recommendation.artist).toBe("Gamma");
  });

  it("omits outside-profile when no album is below the score threshold", () => {
    const highlights = buildAktuellHighlights([
      recommendation({
        artist: "Alpha",
        album: "First",
        rating: 8,
        score: 0.9,
      }),
      recommendation({
        artist: "Beta",
        album: "Second",
        rating: 9,
        score: 0.8,
      }),
    ]);

    expect(highlights).toHaveLength(2);
    expect(highlights.map((item) => item.label)).toEqual([
      "Beste Passung",
      "Kritikerfavorit",
    ]);
  });

  it("returns an empty list when no recommendations are available", () => {
    expect(buildAktuellHighlights([])).toEqual([]);
  });
});
