import { describe, expect, it } from "vitest";

import {
  applyCommunityMapChoice,
  communityChoicesFromLikedIds,
  cycleCommunityMapChoice,
  likedCommunityIds,
  pruneCommunityMapChoices,
  resetCommunityMapChoices,
  summarizeCommunityMapChoices,
} from "./communityMapChoice";

describe("communityMapChoice", () => {
  it("cycles through unset, liked, and disliked", () => {
    expect(cycleCommunityMapChoice("unset")).toBe("liked");
    expect(cycleCommunityMapChoice("liked")).toBe("disliked");
    expect(cycleCommunityMapChoice("disliked")).toBe("unset");
  });

  it("removes unset choices from the map record", () => {
    const next = applyCommunityMapChoice({ C001: "liked" }, "C001", "unset");
    expect(next).toEqual({});
  });

  it("summarizes reviewed communities for the visible set", () => {
    const summary = summarizeCommunityMapChoices(
      { C001: "liked", C002: "disliked", C003: "unset" },
      ["C001", "C002", "C003", "C004"],
    );
    expect(summary).toEqual({
      liked: 1,
      disliked: 1,
      reviewed: 2,
      total: 4,
      unset: 2,
    });
  });

  it("clears choices for the requested community ids", () => {
    const next = resetCommunityMapChoices(
      { C001: "liked", C002: "disliked", C003: "liked" },
      ["C001", "C002"],
    );
    expect(next).toEqual({ C003: "liked" });
  });

  it("derives liked ids and prunes removed communities", () => {
    const choices = communityChoicesFromLikedIds(["C001", "C002"]);
    expect(likedCommunityIds(choices)).toEqual(["C001", "C002"]);
    expect(pruneCommunityMapChoices(choices, ["C002"])).toEqual({ C002: "liked" });
  });
});
