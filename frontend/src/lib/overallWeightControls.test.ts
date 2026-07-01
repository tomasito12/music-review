import { describe, expect, it } from "vitest";

import { DEFAULT_BALANCED_FILTER_SETTINGS } from "./plattenradarApi";
import {
  normalizedOverallShares,
  overallSharePercents,
  updateOverallWeightShare,
} from "./overallWeightControls";

describe("overallWeightControls", () => {
  it("normalizes raw weights to shares that sum to one", () => {
    const shares = normalizedOverallShares({
      ...DEFAULT_BALANCED_FILTER_SETTINGS,
      overall_weight_alpha: 0.7,
      overall_weight_beta: 0.1,
      overall_weight_gamma: 0.2,
    });
    expect(shares[0]).toBeCloseTo(0.7);
    expect(shares[1]).toBeCloseTo(0.1);
    expect(shares[2]).toBeCloseTo(0.2);
  });

  it("redistributes other shares when one share increases", () => {
    const next = updateOverallWeightShare(
      DEFAULT_BALANCED_FILTER_SETTINGS,
      "overall_weight_alpha",
      80,
    );
    const percents = overallSharePercents(next);
    expect(percents[0]).toBe(80);
    expect(percents.reduce((sum, value) => sum + value, 0)).toBe(100);
  });

  it("handles zero total weights with equal fallback shares", () => {
    const shares = normalizedOverallShares({
      ...DEFAULT_BALANCED_FILTER_SETTINGS,
      overall_weight_alpha: 0,
      overall_weight_beta: 0,
      overall_weight_gamma: 0,
    });
    expect(shares).toEqual([1 / 3, 1 / 3, 1 / 3]);
  });
});
