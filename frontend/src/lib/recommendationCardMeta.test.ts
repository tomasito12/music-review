import { describe, expect, it } from "vitest";

import { recommendationCardMetaParts } from "./recommendationCardMeta";

describe("recommendationCardMetaParts", () => {
  it("includes year and rating", () => {
    expect(
      recommendationCardMetaParts({ year: 2024, rating: 8 }),
    ).toEqual(["2024", "8/10 bei plattentests.de"]);
  });

  it("appends record label when present", () => {
    expect(
      recommendationCardMetaParts({
        year: 2021,
        rating: 7,
        recordLabel: "City Slang",
      }),
    ).toEqual(["2021", "7/10 bei plattentests.de", "City Slang"]);
  });

  it("omits empty record label", () => {
    expect(
      recommendationCardMetaParts({
        year: 2021,
        rating: 7,
        recordLabel: "",
      }),
    ).toEqual(["2021", "7/10 bei plattentests.de"]);
  });
});
