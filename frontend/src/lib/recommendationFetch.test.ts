import { describe, expect, it } from "vitest";

import { shouldRefetchRecommendations } from "./recommendationFetch";

describe("shouldRefetchRecommendations", () => {
  it("fetches when no recommendations are cached", () => {
    expect(shouldRefetchRecommendations(null, 0, -1)).toBe(true);
  });

  it("skips fetch when cached data matches the handled reload token", () => {
    expect(shouldRefetchRecommendations([{ id: 1 }], 2, 2)).toBe(false);
  });

  it("refetches when reload token changed but stale cache remains", () => {
    expect(shouldRefetchRecommendations([{ id: 1 }], 3, 2)).toBe(true);
  });
});
