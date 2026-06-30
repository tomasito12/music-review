import { describe, expect, it } from "vitest";

import { pickExampleCommunityIds } from "./profileSetupExampleCommunities";
import type { TasteCommunityOption } from "./plattenradarApi";

const communities: TasteCommunityOption[] = [
  {
    id: "C001",
    label: "Indie Rock",
    broad_categories: ["Rock & Alternative"],
    example_artists: [],
  },
  {
    id: "C002",
    label: "Indie Pop",
    broad_categories: ["Rock & Alternative"],
    example_artists: [],
  },
  {
    id: "C003",
    label: "Elektronik",
    broad_categories: ["Electronic & Dance"],
    example_artists: [],
  },
  {
    id: "C004",
    label: "Jazz",
    broad_categories: ["Jazz & Soul"],
    example_artists: [],
  },
];

describe("pickExampleCommunityIds", () => {
  it("picks one community per broad category up to three ids", () => {
    expect(pickExampleCommunityIds(communities)).toEqual(["C001", "C003", "C004"]);
  });

  it("falls back to the first three communities when categories are missing", () => {
    const withoutCategories: TasteCommunityOption[] = [
      { id: "A", label: "A", broad_categories: [], example_artists: [] },
      { id: "B", label: "B", broad_categories: [], example_artists: [] },
      { id: "C", label: "C", broad_categories: [], example_artists: [] },
    ];
    expect(pickExampleCommunityIds(withoutCategories)).toEqual(["A", "B", "C"]);
  });
});
