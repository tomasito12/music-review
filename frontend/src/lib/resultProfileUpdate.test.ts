import { describe, expect, it } from "vitest";

import {
  buildProfileSessionFromPreset,
  buildUpdatedProfileSession,
} from "./resultProfileUpdate";
import type { ProfileSetupResult } from "./profileSessionStorage";
import type { TastePreset } from "./plattenradarApi";

const session: ProfileSetupResult = {
  presetId: "balanced",
  presetLabel: "Ausgewogen",
  profile: {
    name: "Temporäres Musikprofil",
    selected_communities: ["C001", "C002"],
    community_weights_raw: { C001: 0.5, C002: 0.5 },
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

const precisePreset: TastePreset = {
  id: "precise",
  label: "Treffsicher",
  subtitle: "Nah an deinem Profil",
  description: "Sortiert stärker nach Stilpassung.",
  icon: "crosshair",
  filter_settings: {
    community_spectrum_crossover: 0.5,
    overall_weight_alpha: 0.7,
    overall_weight_beta: 0.2,
    overall_weight_gamma: 0.1,
    rating_max: 10,
    rating_min: 6,
    score_max: 1,
    score_min: 0.4,
    serendipity: 0,
    sort_mode: "deterministic",
  },
};

describe("buildUpdatedProfileSession", () => {
  it("updates filter settings while keeping selected communities", () => {
    const next = buildUpdatedProfileSession(session, {
      filterSettings: {
        ...session.profile.filter_settings,
        score_min: 0.55,
      },
    });

    expect(next.profile.selected_communities).toEqual(["C001", "C002"]);
    expect(next.profile.filter_settings.score_min).toBe(0.55);
    expect(next.presetId).toBe("balanced");
  });

  it("updates community weights", () => {
    const next = buildUpdatedProfileSession(session, {
      communityWeightsRaw: { C001: 0.7, C002: 0.3 },
    });

    expect(next.profile.community_weights_raw).toEqual({ C001: 0.7, C002: 0.3 });
  });
});

describe("buildProfileSessionFromPreset", () => {
  it("switches preset label and filter settings", () => {
    const next = buildProfileSessionFromPreset(session, precisePreset);

    expect(next.presetId).toBe("precise");
    expect(next.presetLabel).toBe("Treffsicher");
    expect(next.profile.filter_settings.overall_weight_alpha).toBe(0.7);
  });
});
