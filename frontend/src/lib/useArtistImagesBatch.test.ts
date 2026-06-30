import { describe, expect, it } from "vitest";

import { pendingArtistImageLookups } from "./useArtistImagesBatch";

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
