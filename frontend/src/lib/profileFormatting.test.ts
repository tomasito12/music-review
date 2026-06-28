import { describe, expect, it } from "vitest";

import { formatCommunityExampleArtists } from "./profileFormatting";

describe("formatCommunityExampleArtists", () => {
  it("returns empty text for missing artists", () => {
    expect(formatCommunityExampleArtists([])).toBe("");
  });

  it("formats up to three artists with the Streamlit prefix", () => {
    expect(formatCommunityExampleArtists(["A", "B", "C"])).toBe("z. B. A, B, C");
  });

  it("shortens to two names when three exceed the caption limit", () => {
    const longA = "X".repeat(18);
    const longB = "Y".repeat(18);
    const longC = "Z".repeat(18);
    expect(formatCommunityExampleArtists([longA, longB, longC])).toBe(
      `z. B. ${longA}, ${longB}`,
    );
  });

  it("swaps to shorter names so the caption stays on one line", () => {
    const longName = "X".repeat(35);
    const shortA = "Short A";
    const shortB = "Short B";
    expect(formatCommunityExampleArtists([longName, shortA, shortB])).toBe(
      "z. B. Short A, Short B",
    );
  });
});
