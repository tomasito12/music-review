import { describe, expect, it } from "vitest";

import { createTemporaryTasteProfile } from "./plattenradarApi";
import { cloneTasteProfile, tasteProfilesMatch } from "./profileComparison";

describe("tasteProfilesMatch", () => {
  it("returns true for equivalent profiles", () => {
    const left = createTemporaryTasteProfile(["C001", "C002"]);
    const right = cloneTasteProfile(left);

    expect(tasteProfilesMatch(left, right)).toBe(true);
  });

  it("returns false when community selection differs", () => {
    const left = createTemporaryTasteProfile(["C001"]);
    const right = createTemporaryTasteProfile(["C001", "C002"]);

    expect(tasteProfilesMatch(left, right)).toBe(false);
  });
});
