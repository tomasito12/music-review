import { describe, expect, it } from "vitest";

import {
  chunkArtistImageLookups,
  markPendingArtistImagesUnavailable,
  pendingArtistImageLookups,
} from "./useArtistImagesBatch";

describe("pendingArtistImageLookups", () => {
  it("returns only artists without a resolved image lookup", () => {
    const resolved = new Map([
      ["mbid-alpha", { artistName: "Alpha" } as never],
      ["name:beta", null],
    ]);

    expect(
      pendingArtistImageLookups(
        [
          { artistMbid: "mbid-alpha", artistName: "Alpha" },
          { artistName: "Beta" },
          { artistMbid: "mbid-gamma", artistName: "Gamma" },
        ],
        resolved,
      ),
    ).toEqual([{ artistMbid: "mbid-gamma", artistName: "Gamma" }]);
  });
});

describe("chunkArtistImageLookups", () => {
  it("splits lookups into batches of ten", () => {
    const lookups = Array.from({ length: 12 }, (_, index) => ({
      artistMbid: `mbid-${index + 1}`,
      artistName: `Artist ${index + 1}`,
    }));

    expect(chunkArtistImageLookups(lookups)).toEqual([
      lookups.slice(0, 10),
      lookups.slice(10),
    ]);
  });
});

describe("markPendingArtistImagesUnavailable", () => {
  it("marks unresolved pending artists as null", () => {
    const merged = markPendingArtistImagesUnavailable(
      [{ artistMbid: "mbid-fail", artistName: "Fail Artist" }],
      new Map(),
    );

    expect(merged.get("mbid-fail")).toBeNull();
  });
});
