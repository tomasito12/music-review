import { describe, expect, it } from "vitest";

import {
  COMMUNITY_TAG_MIN_AFFINITY,
  recommendationTagStyle,
  visibleRecommendationTags,
} from "./recommendationTagStyles";
import type { RecommendationTag } from "../types";

const sampleTags: RecommendationTag[] = [
  { label: "Indie", affinity: 0.8, matchesProfile: true },
  { label: "Ambient", affinity: 0.15, matchesProfile: false },
  { label: "Noise", affinity: 0.05, matchesProfile: false },
];

describe("visibleRecommendationTags", () => {
  it("drops tags below the minimum affinity threshold", () => {
    expect(visibleRecommendationTags(sampleTags).map((tag) => tag.label)).toEqual([
      "Indie",
      "Ambient",
    ]);
    expect(COMMUNITY_TAG_MIN_AFFINITY).toBe(0.1);
  });
});

describe("recommendationTagStyle", () => {
  it("uses darker reds for stronger affinities", () => {
    expect(recommendationTagStyle(sampleTags[0]).backgroundColor).toBe("#7f1d1d");
    expect(recommendationTagStyle(sampleTags[1]).backgroundColor).toBe("#f5d5d5");
  });
});
