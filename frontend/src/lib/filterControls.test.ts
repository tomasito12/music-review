import { describe, expect, it } from "vitest";

import { DEFAULT_BALANCED_FILTER_SETTINGS } from "./plattenradarApi";
import {
  clampSpectrumCrossover,
  clearYearFilter,
  describeSpectrumCrossover,
  enableYearFilter,
  hasYearFilter,
  snapSpectrumCrossover,
  updateMinimumRating,
  updateStyleMatchMinPercent,
  updateYearFilter,
} from "./filterControls";

describe("updateStyleMatchMinPercent", () => {
  it("sets only the minimum score threshold", () => {
    const next = updateStyleMatchMinPercent(DEFAULT_BALANCED_FILTER_SETTINGS, 55);

    expect(next.score_min).toBe(0.55);
    expect(next.score_max).toBe(1);
  });
});

describe("updateMinimumRating", () => {
  it("keeps the upper rating bound open", () => {
    const next = updateMinimumRating(DEFAULT_BALANCED_FILTER_SETTINGS, 8);

    expect(next.rating_min).toBe(8);
    expect(next.rating_max).toBe(10);
  });
});

describe("year filter helpers", () => {
  it("activates and clears year bounds", () => {
    const enabled = enableYearFilter(DEFAULT_BALANCED_FILTER_SETTINGS);
    expect(hasYearFilter(enabled)).toBe(true);

    const cleared = clearYearFilter(enabled);
    expect(cleared.year_min).toBeNull();
    expect(cleared.year_max).toBeNull();
  });

  it("keeps year bounds ordered", () => {
    const next = updateYearFilter(DEFAULT_BALANCED_FILTER_SETTINGS, 2018, 1990);
    expect(next.year_min).toBe(1990);
    expect(next.year_max).toBe(2018);
  });
});

describe("spectrumCrossover helpers", () => {
  it("keeps stored values continuous while labels use the nearest stop", () => {
    expect(clampSpectrumCrossover(0.48)).toBe(0.48);
    expect(snapSpectrumCrossover(0.48)).toBe(0.5);
    expect(describeSpectrumCrossover(0.48)).toBe("Ausgewogen");
  });
});
