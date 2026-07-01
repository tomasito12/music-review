import { describe, expect, it } from "vitest";

import {
  artistDedupeKeys,
  artistImageLookupKey,
  claimArtist,
  isArtistClaimed,
  isNameLookupKey,
} from "./artistImageLookupKey";

describe("artistImageLookupKey", () => {
  it("uses the MBID when present", () => {
    expect(
      artistImageLookupKey({ artistMbid: "mbid-1", artistName: "Alpha" }),
    ).toBe("mbid-1");
  });

  it("falls back to a stable name key when MBID is missing", () => {
    expect(
      artistImageLookupKey({ artistName: "Sibylle Kefer" }),
    ).toBe("name:sibylle kefer");
  });

  it("detects name lookup keys", () => {
    expect(isNameLookupKey("name:sibylle kefer")).toBe(true);
    expect(isNameLookupKey("mbid-1")).toBe(false);
  });
});

describe("artistDedupeKeys", () => {
  it("includes both MBID and normalized name when available", () => {
    expect(artistDedupeKeys({ artistMbid: "mbid-1", artistName: "Slint" })).toEqual([
      "mbid-1",
      "name:slint",
    ]);
  });

  it("uses only the name key when MBID is missing", () => {
    expect(artistDedupeKeys({ artistName: "Slint" })).toEqual(["name:slint"]);
  });
});

describe("claimArtist", () => {
  it("blocks later claims by either MBID or name", () => {
    const claimed = new Set<string>();
    claimArtist({ artistMbid: "mbid-slint", artistName: "Slint" }, claimed);

    expect(
      isArtistClaimed({ artistName: "Slint" }, claimed),
    ).toBe(true);
    expect(
      isArtistClaimed({ artistMbid: "mbid-other", artistName: "Slint" }, claimed),
    ).toBe(true);
    expect(
      isArtistClaimed({ artistMbid: "mbid-beta", artistName: "Beta" }, claimed),
    ).toBe(false);
  });
});
