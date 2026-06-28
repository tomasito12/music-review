import { describe, expect, it } from "vitest";

import {
  buildProfileOverviewSummary,
  deriveBroadCategories,
} from "./profileOverviewSummary";
import type { ProfileSetupResult } from "./profileSessionStorage";
import type { TasteCommunityOption } from "./plattenradarApi";

const communities: TasteCommunityOption[] = [
  {
    id: "C001",
    label: "Indie Rock",
    broad_categories: ["Rock"],
    example_artists: ["Band A"],
  },
  {
    id: "C002",
    label: "Kraut",
    broad_categories: ["Rock", "Experimental"],
    example_artists: ["Band B"],
  },
  {
    id: "C003",
    label: "Ambient",
    broad_categories: ["Electronic"],
    example_artists: ["Band C"],
  },
];

const session: ProfileSetupResult = {
  presetId: "balanced",
  presetLabel: "Ausgewogen",
  profile: {
    name: "Temporäres Musikprofil",
    selected_communities: ["C001", "C002", "C003"],
    community_weights_raw: { C001: 0.5, C002: 0.5, C003: 0.5 },
    filter_settings: {
      community_spectrum_crossover: 0.5,
      overall_weight_alpha: 0.5,
      overall_weight_beta: 0.25,
      overall_weight_gamma: 0.25,
      rating_max: 10,
      rating_min: 6,
      score_max: 1,
      score_min: 0.4,
      serendipity: 0,
      sort_mode: "deterministic",
    },
  },
};

describe("deriveBroadCategories", () => {
  it("returns sorted unique broad categories", () => {
    expect(deriveBroadCategories(["C001", "C002"], communities)).toEqual([
      "Experimental",
      "Rock",
    ]);
  });
});

describe("buildProfileOverviewSummary", () => {
  it("builds overview text and filter chips", () => {
    expect(buildProfileOverviewSummary(session, communities)).toEqual({
      broadCategories: ["Electronic", "Experimental", "Rock"],
      broadCategoriesText: "Electronic, Experimental, Rock",
      detailStyleCount: 3,
      detailStylePreview: ["Ambient", "Indie Rock", "Kraut"],
      detailStyleOverflow: 0,
      detailStylesText: "3 Detailstile: Ambient, Indie Rock, Kraut",
      presetLabel: "Ausgewogen",
      filterChips: [
        "Ausgewogen",
        "Stilpassung mindestens 40 %",
        "Wertung 6–10",
        "Stabile Reihenfolge",
      ],
    });
  });

  it("handles empty selections", () => {
    const emptySession: ProfileSetupResult = {
      ...session,
      profile: {
        ...session.profile,
        selected_communities: [],
        community_weights_raw: {},
      },
    };

    expect(buildProfileOverviewSummary(emptySession, communities)).toMatchObject({
      broadCategoriesText: "Noch keine Richtungen gewählt",
      detailStylesText: "Noch keine Detailstile gewählt",
      detailStyleCount: 0,
    });
  });

  it("truncates long detail-style lists", () => {
    const manyCommunities = Array.from({ length: 7 }, (_, index) => ({
      id: `C10${index}`,
      label: `Stil ${index + 1}`,
      broad_categories: ["Rock"],
      example_artists: [],
    }));
    const manySession: ProfileSetupResult = {
      ...session,
      profile: {
        ...session.profile,
        selected_communities: manyCommunities.map((community) => community.id),
      },
    };

    const summary = buildProfileOverviewSummary(manySession, manyCommunities);
    expect(summary.detailStyleOverflow).toBe(2);
    expect(summary.detailStylesText).toContain("+2 weitere");
  });
});
