import { describe, expect, it } from "vitest";

import {
  buildEntdeckenHeaderMessage,
  buildEntdeckenPhotoTileIndices,
  entdeckenHighlightArtistLookupKeys,
  entdeckenHighlightRanks,
  entdeckenPhotoLookupRecommendations,
  entdeckenPhotoSlotGroups,
  entdeckenPhotoTileStartIndex,
  entdeckenRecommendationHasPhoto,
  formatEntdeckenHighlightKicker,
  formatRankPhotoKicker,
  recurringPhotoSlotCandidates,
  resolveEntdeckenPhotoRanks,
  selectEntdeckenHighlightsFromPhotoPool,
} from "./entdeckenPage";
import type { ArtistImageData } from "./artistImageApi";
import type { Recommendation } from "../types";

function recommendation(
  rank: number,
  artist = `Artist ${rank}`,
  overrides: Partial<Recommendation> = {},
): Recommendation {
  return {
    rank,
    reviewId: rank,
    artist,
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
    ...overrides,
  };
}

describe("recurringPhotoSlotCandidates", () => {
  it("tries the anchor rank before nearby fallbacks", () => {
    expect(recurringPhotoSlotCandidates(6)).toEqual([6, 7, 4, 8, 9]);
    expect(recurringPhotoSlotCandidates(12)).toEqual([12, 13, 10, 14, 15]);
  });
});

describe("entdeckenPhotoSlotGroups", () => {
  it("starts with the first-rank group and then anchors every six ranks", () => {
    expect(entdeckenPhotoSlotGroups(13)).toEqual([
      [1, 2, 3, 4, 5],
      [6, 7, 4, 8, 9],
      [12, 13, 10, 14, 15],
    ]);
  });

  it("returns no groups for an empty archive result", () => {
    expect(entdeckenPhotoSlotGroups(0)).toEqual([]);
  });

  it("drops excluded highlight ranks from slot groups", () => {
    expect(entdeckenPhotoSlotGroups(13, new Set([1, 2, 3]))).toEqual([
      [4, 5],
      [6, 7, 4, 8, 9],
      [12, 13, 10, 14, 15],
    ]);
  });
});

describe("resolveEntdeckenPhotoRanks", () => {
  const recommendations = Array.from({ length: 15 }, (_, index) =>
    recommendation(index + 1),
  );

  it("prefers rank 1 for the first photo slot when an image exists", () => {
    const photoRanks = resolveEntdeckenPhotoRanks(
      recommendations,
      (item) => item.rank === 1 || item.rank === 6 || item.rank === 12,
    );

    expect([...photoRanks]).toEqual([1, 6, 12]);
  });

  it("falls back within a slot group before moving to the next anchor", () => {
    const photoRanks = resolveEntdeckenPhotoRanks(
      recommendations,
      (item) => item.rank === 7 || item.rank === 13,
    );

    expect([...photoRanks]).toEqual([7, 13]);
  });

  it("uses rank 4 when higher-priority candidates in the recurring group have no photo", () => {
    const photoRanks = resolveEntdeckenPhotoRanks(
      recommendations,
      (item) => item.rank === 4 || item.rank === 10,
    );

    expect([...photoRanks]).toEqual([4, 10]);
  });

  it("does not assign duplicate ranks across slot groups", () => {
    const photoRanks = resolveEntdeckenPhotoRanks(recommendations, (item) => item.rank <= 5);

    expect([...photoRanks]).toEqual([1, 4]);
  });

  it("skips highlight ranks when resolving photo slots", () => {
    const photoRanks = resolveEntdeckenPhotoRanks(
      recommendations,
      (item) => item.rank === 4 || item.rank === 7 || item.rank === 13,
      new Set([1, 2, 3]),
    );

    expect([...photoRanks]).toEqual([4, 7, 13]);
  });

  it("does not reuse the same artist photo across list slots", () => {
    const sameArtistTwice = [
      recommendation(1, "Alpha", { artistMbid: "mbid-alpha" }),
      recommendation(2, "Alpha", { album: "Album 2", artistMbid: "mbid-alpha" }),
      recommendation(6, "Beta", { artistMbid: "mbid-beta" }),
      ...Array.from({ length: 9 }, (_, index) =>
        recommendation(index + 3, `Artist ${index + 3}`, {
          artistMbid: `mbid-${index + 3}`,
        }),
      ).filter((item) => item.rank !== 6),
    ];

    const photoRanks = resolveEntdeckenPhotoRanks(sameArtistTwice, (item) =>
      ["mbid-alpha", "mbid-beta"].includes(item.artistMbid ?? ""),
    );

    expect(photoRanks.has(1)).toBe(true);
    expect(photoRanks.has(2)).toBe(false);
    expect(photoRanks.has(6)).toBe(true);
  });

  it("skips artists already shown in Entdecken highlights", () => {
    const photoRanks = resolveEntdeckenPhotoRanks(
      recommendations,
      (item) => item.rank <= 8,
      new Set(),
      new Set(["mbid-1"]),
    );

    expect(photoRanks.has(1)).toBe(false);
    expect([...photoRanks].length).toBeGreaterThan(0);
  });
});

describe("entdeckenPhotoLookupRecommendations", () => {
  it("returns unique recommendations for all candidate ranks in the loaded list", () => {
    const recommendations = Array.from({ length: 9 }, (_, index) =>
      recommendation(index + 1),
    );

    expect(
      entdeckenPhotoLookupRecommendations(recommendations).map((item) => item.rank),
    ).toEqual([1, 2, 3, 4, 5, 6, 7, 8, 9]);
  });
});

describe("entdeckenRecommendationHasPhoto", () => {
  it("returns false without a lookup key or resolved image", () => {
    const itemWithoutMbid = {
      ...recommendation(1),
      artist: "",
      artistMbid: undefined,
    };
    const images = new Map<string, ArtistImageData | null>([["mbid-1", null]]);
    const resolvedImage: ArtistImageData = {
      artistMbid: "mbid-1",
      artistName: "Artist 1",
      thumbnailUrl: "https://example.com/image.jpg",
      attributionText: "Test",
      license: "CC-BY",
      sourceUrl: "https://example.com/source",
    };

    expect(entdeckenRecommendationHasPhoto(itemWithoutMbid, images)).toBe(false);
    expect(entdeckenRecommendationHasPhoto(recommendation(1), images)).toBe(false);
    expect(
      entdeckenRecommendationHasPhoto(
        recommendation(1),
        new Map([["mbid-1", resolvedImage]]),
      ),
    ).toBe(true);
  });
});

describe("buildEntdeckenPhotoTileIndices", () => {
  it("offsets alternating indices when rank 1 is a photo tile", () => {
    const recommendations = Array.from({ length: 8 }, (_, index) =>
      recommendation(index + 1),
    );
    const photoRanks = new Set([1, 6]);

    expect(entdeckenPhotoTileStartIndex(recommendations, photoRanks)).toBe(1);
    expect(buildEntdeckenPhotoTileIndices(recommendations, photoRanks)).toEqual(
      new Map([
        [1, 1],
        [6, 2],
      ]),
    );
  });
});

describe("formatRankPhotoKicker", () => {
  it("formats rank numbers as zero-padded Platz labels", () => {
    expect(formatRankPhotoKicker(1)).toBe("Platz 01");
    expect(formatRankPhotoKicker(12)).toBe("Platz 12");
  });
});

describe("formatEntdeckenHighlightKicker", () => {
  it("combines category label and archive rank", () => {
    expect(formatEntdeckenHighlightKicker("Kritikerfavorit", 9)).toBe(
      "Kritikerfavorit · Platz 09",
    );
  });
});

describe("selectEntdeckenHighlightsFromPhotoPool", () => {
  it("returns four distinct photo-backed highlight roles", () => {
    const pool = [
      recommendation(1, "Alpha", { score: 0.95, rating: 7, styleFit: 0.7, albumStyleBreadth: 0.2 }),
      recommendation(2, "Beta", { score: 0.7, rating: 10, styleFit: 0.6, albumStyleBreadth: 0.4 }),
      recommendation(3, "Gamma", { score: 0.8, rating: 8, styleFit: 0.5, albumStyleBreadth: 0.9 }),
      recommendation(4, "Delta", { score: 0.6, rating: 9, styleFit: 0.95, albumStyleBreadth: 0.3 }),
    ];

    const highlights = selectEntdeckenHighlightsFromPhotoPool(pool);

    expect(highlights).toHaveLength(4);
    expect(highlights[0]?.label).toBe("Beste Gesamtpassung");
    expect(highlights[0]?.recommendation.artist).toBe("Alpha");
    expect(highlights[1]?.label).toBe("Kritikerfavorit");
    expect(highlights[1]?.recommendation.artist).toBe("Beta");
    expect(highlights[2]?.label).toBe("Stilistisch breit");
    expect(highlights[2]?.recommendation.artist).toBe("Gamma");
    expect(highlights[3]?.label).toBe("Höchste Passung");
    expect(highlights[3]?.recommendation.artist).toBe("Delta");
  });

  it("skips the overall winner when picking the critic favorite", () => {
    const pool = [
      recommendation(1, "Same", { score: 0.95, rating: 10, styleFit: 0.9, albumStyleBreadth: 0.9 }),
      recommendation(2, "Other", { score: 0.7, rating: 9, styleFit: 0.5, albumStyleBreadth: 0.2 }),
    ];

    const highlights = selectEntdeckenHighlightsFromPhotoPool(pool);
    const critic = highlights.find((item) => item.label === "Kritikerfavorit");

    expect(critic?.recommendation.artist).toBe("Other");
  });

  it("uses each artist photo at most once across highlight roles", () => {
    const pool = [
      recommendation(1, "Same", { album: "A", artistMbid: "mbid-same", score: 0.95, rating: 10 }),
      recommendation(2, "Same", { album: "B", artistMbid: "mbid-same", score: 0.7, rating: 9 }),
      recommendation(3, "Other", { artistMbid: "mbid-other", score: 0.6, rating: 8 }),
    ];

    const highlights = selectEntdeckenHighlightsFromPhotoPool(pool);
    const lookupKeys = highlights.map((item) => item.recommendation.artistMbid);

    expect(new Set(lookupKeys).size).toBe(lookupKeys.length);
    expect(lookupKeys.filter((mbid) => mbid === "mbid-same")).toHaveLength(1);
  });

  it("returns an empty list without recommendations", () => {
    expect(selectEntdeckenHighlightsFromPhotoPool([])).toEqual([]);
  });
});

describe("entdeckenHighlightArtistLookupKeys", () => {
  it("collects artist lookup keys from highlight cards", () => {
    const highlights = selectEntdeckenHighlightsFromPhotoPool([
      recommendation(1, "Alpha", { score: 0.95, rating: 7, styleFit: 0.7, albumStyleBreadth: 0.2 }),
      recommendation(2, "Beta", { score: 0.7, rating: 10, styleFit: 0.6, albumStyleBreadth: 0.4 }),
      recommendation(3, "Gamma", { score: 0.8, rating: 8, styleFit: 0.5, albumStyleBreadth: 0.9 }),
      recommendation(4, "Delta", { score: 0.6, rating: 9, styleFit: 0.95, albumStyleBreadth: 0.3 }),
    ]);

    expect([...entdeckenHighlightArtistLookupKeys(highlights)].sort()).toEqual([
      "mbid-1",
      "mbid-2",
      "mbid-3",
      "mbid-4",
    ]);
  });
});

describe("entdeckenHighlightRanks", () => {
  it("collects ranks from highlight cards", () => {
    const highlights = selectEntdeckenHighlightsFromPhotoPool([
      recommendation(1, "Alpha", { score: 0.95, rating: 7, styleFit: 0.7, albumStyleBreadth: 0.2 }),
      recommendation(2, "Beta", { score: 0.7, rating: 10, styleFit: 0.6, albumStyleBreadth: 0.4 }),
      recommendation(3, "Gamma", { score: 0.8, rating: 8, styleFit: 0.5, albumStyleBreadth: 0.9 }),
      recommendation(4, "Delta", { score: 0.6, rating: 9, styleFit: 0.95, albumStyleBreadth: 0.3 }),
    ]);

    expect([...entdeckenHighlightRanks(highlights)].sort()).toEqual([1, 2, 3, 4]);
  });
});

describe("buildEntdeckenHeaderMessage", () => {
  it("describes an empty archive result", () => {
    expect(buildEntdeckenHeaderMessage(0, 0)).toContain("nichts Passendes");
  });

  it("describes partial and complete archive loads", () => {
    expect(buildEntdeckenHeaderMessage(40, 20)).toContain("40 Alben");
    expect(buildEntdeckenHeaderMessage(40, 20)).toContain("20 werden gerade angezeigt");
    expect(buildEntdeckenHeaderMessage(12, 12)).toContain("werden angezeigt");
  });
});
