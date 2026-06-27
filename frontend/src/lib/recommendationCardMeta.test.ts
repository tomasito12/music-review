import { describe, expect, it } from "vitest";

import {
  formatReleaseDate,
  recommendationCardMetaParts,
} from "./recommendationCardMeta";

describe("formatReleaseDate", () => {
  it("formats ISO dates for German display", () => {
    expect(formatReleaseDate("2024-05-01", 2024)).toBe("01.05.2024");
  });

  it("falls back to year when no release date is available", () => {
    expect(formatReleaseDate(undefined, 2021)).toBe("2021");
  });
});

describe("recommendationCardMetaParts", () => {
  it("includes release date, rating and score", () => {
    expect(
      recommendationCardMetaParts({
        year: 2024,
        releaseDate: "2024-05-01",
        rating: 8,
        score: 0.84,
      }),
    ).toEqual(["01.05.2024", "8/10 bei plattentests.de", "Score 0.84"]);
  });

  it("appends plattenlabel when present", () => {
    expect(
      recommendationCardMetaParts({
        year: 2021,
        releaseDate: "2021-03-12",
        rating: 7,
        score: 0.71,
        recordLabel: "City Slang",
      }),
    ).toEqual([
      "12.03.2021",
      "7/10 bei plattentests.de",
      "Score 0.71",
      "Plattenlabel: City Slang",
    ]);
  });

  it("omits empty record label", () => {
    expect(
      recommendationCardMetaParts({
        year: 2021,
        rating: 7,
        score: 0.71,
        recordLabel: "",
      }),
    ).toEqual(["2021", "7/10 bei plattentests.de", "Score 0.71"]);
  });
});
