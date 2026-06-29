export const VISUAL_PROFILE_SESSION = {
  presetId: "balanced",
  presetLabel: "Ausgewogen",
  savedAt: "2026-06-27T12:00:00.000Z",
  profile: {
    name: "Temporäres Musikprofil",
    selected_communities: ["C001", "C002", "C003"],
    community_weights_raw: { C001: 0.5, C002: 0.5, C003: 0.5 },
    filter_settings: {
      rating_min: 6,
      rating_max: 10,
      score_min: 0.4,
      score_max: 1,
      overall_weight_alpha: 0.7,
      overall_weight_beta: 0.1,
      overall_weight_gamma: 0.2,
      sort_mode: "deterministic",
      serendipity: 0,
    },
  },
} as const;

export const VISUAL_API_BASE_URL =
  process.env.PLAYWRIGHT_API_BASE_URL ?? "http://127.0.0.1:8010";

export const VISUAL_PROFILE_STORAGE_KEY = "plattenradar.profile-session.v1";
