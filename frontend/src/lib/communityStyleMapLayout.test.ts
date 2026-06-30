import { describe, expect, it } from "vitest";

import {
  communityMapNodeById,
  communityMapNodeRadius,
  isProfileStyleMapEnabled,
  mapPointToSvg,
} from "./communityStyleMapLayout";

describe("communityStyleMapLayout", () => {
  it("maps normalized coordinates into svg viewbox units", () => {
    expect(mapPointToSvg({ x: 0.5, y: 0.25 })).toEqual({ x: 500, y: 250 });
  });

  it("scales node radius relative to community sizes", () => {
    const sizes = [10, 100];
    expect(communityMapNodeRadius({ size: 10 }, sizes)).toBeLessThan(
      communityMapNodeRadius({ size: 100 }, sizes),
    );
  });

  it("indexes map nodes by community id", () => {
    const lookup = communityMapNodeById([
      { id: "C001", x: 0.1, y: 0.2, size: 5, neighbors: [] },
      { id: "C002", x: 0.8, y: 0.4, size: 8, neighbors: ["C001"] },
    ]);
    expect(lookup.get("C002")?.neighbors).toEqual(["C001"]);
  });

  it("keeps the style map enabled unless explicitly disabled", () => {
    expect(isProfileStyleMapEnabled()).toBe(true);
  });
});
