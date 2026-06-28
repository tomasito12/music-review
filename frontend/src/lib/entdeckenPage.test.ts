import { describe, expect, it } from "vitest";

import {
  buildEntdeckenHeaderMessage,
  buildEntdeckenPhotoTileIndices,
  entdeckenPhotoLookupRecommendations,
  entdeckenPhotoSlotGroups,
  entdeckenPhotoTileStartIndex,
  entdeckenRecommendationHasPhoto,
  formatRankPhotoKicker,
  recurringPhotoSlotCandidates,
  resolveEntdeckenPhotoRanks,
} from "./entdeckenPage";
import type { ArtistImageData } from "./artistImageApi";
import type { Recommendation } from "../types";

function recommendation(rank: number, artist = `Artist ${rank}`): Recommendation {
  return {
    rank,
    reviewId: rank,
    artist,
    album: `Album ${rank}`,
    year: 2024,
    rating: 8,
    score: 0.8,
    fitLabel: "Passend",
    fitPercent: 80,
    excerpt: `Excerpt ${rank}`,
    reviewUrl: `https://example.com/${rank}`,
    tags: [],
    source: "entdecken",
    artistMbid: `mbid-${rank}`,
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
