import { describe, expect, it } from "vitest";

import {
  DEFAULT_COMMUNITY_WEIGHT_RAW,
  communityWeightBiasFromStored,
  communityWeightStoredFromBias,
  migrateLegacyCommunityWeights,
  normalizeCommunityWeights,
  pruneCommunityWeights,
  updateCommunityWeightBias,
} from "./communityWeightMapping";

describe("communityWeightStoredFromBias", () => {
  it("maps neutral bias to the default stored weight", () => {
    expect(communityWeightStoredFromBias(0)).toBe(DEFAULT_COMMUNITY_WEIGHT_RAW);
  });

  it("maps endpoints to 0 and 1", () => {
    expect(communityWeightStoredFromBias(-1)).toBe(0);
    expect(communityWeightStoredFromBias(1)).toBe(1);
  });
});

describe("communityWeightBiasFromStored", () => {
  it("round-trips stored weights through bias", () => {
    const stored = 0.35;
    const bias = communityWeightBiasFromStored(stored);
    expect(communityWeightStoredFromBias(bias)).toBeCloseTo(stored);
  });
});

describe("normalizeCommunityWeights", () => {
  it("fills missing selected communities with the neutral default", () => {
    expect(normalizeCommunityWeights(["C001", "C002"], { C001: 0.8 })).toEqual({
      C001: 0.8,
      C002: DEFAULT_COMMUNITY_WEIGHT_RAW,
    });
  });
});

describe("pruneCommunityWeights", () => {
  it("removes weights for deselected communities", () => {
    expect(
      pruneCommunityWeights(["C001"], { C001: 0.5, C002: 0.9 }),
    ).toEqual({ C001: 0.5 });
  });
});

describe("migrateLegacyCommunityWeights", () => {
  it("maps the old default of 1.0 back to neutral", () => {
    expect(
      migrateLegacyCommunityWeights({ C001: 1, C002: 1 }),
    ).toEqual({
      C001: DEFAULT_COMMUNITY_WEIGHT_RAW,
      C002: DEFAULT_COMMUNITY_WEIGHT_RAW,
    });
  });

  it("keeps mixed weights unchanged", () => {
    expect(migrateLegacyCommunityWeights({ C001: 1, C002: 0.8 })).toEqual({
      C001: 1,
      C002: 0.8,
    });
  });
});

describe("updateCommunityWeightBias", () => {
  it("stores the converted weight for one community", () => {
    expect(updateCommunityWeightBias({}, "C001", 1)).toEqual({ C001: 1 });
  });
});
