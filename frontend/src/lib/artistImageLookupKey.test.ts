import { describe, expect, it } from "vitest";

import {
  artistImageLookupKey,
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
