import { describe, expect, it, vi } from "vitest";

import { AUTH_SESSION_STORAGE_KEY } from "./authSessionStorage";
import { resolveInitialRoute, shouldLandOnAktuell } from "./initialRoute";
import { PROFILE_SESSION_STORAGE_KEY } from "./profileSessionStorage";

describe("resolveInitialRoute", () => {
  it("keeps explicit deep links", () => {
    expect(resolveInitialRoute("/entdecken")).toBe("entdecken");
    expect(resolveInitialRoute("/playlists")).toBe("playlists");
  });

  it("opens aktuell for returning logged-in users on the home path", () => {
    vi.stubGlobal("window", {
      sessionStorage: {
        getItem: (key: string) =>
          key === PROFILE_SESSION_STORAGE_KEY
            ? JSON.stringify({
                presetId: "saved",
                presetLabel: "Gespeichertes Profil",
                savedAt: "2026-06-26T00:00:00.000Z",
                profile: {
                  name: "Profil",
                  selected_communities: ["C001"],
                  community_weights_raw: { C001: 1 },
                  filter_settings: {
                    rating_min: 6,
                    rating_max: 10,
                    score_min: 0.4,
                    score_max: 1,
                    overall_weight_alpha: 0.5,
                    overall_weight_beta: 0.25,
                    overall_weight_gamma: 0.25,
                    sort_mode: "deterministic",
                    serendipity: 0,
                  },
                },
              })
            : null,
      },
      localStorage: {
        getItem: (key: string) =>
          key === AUTH_SESSION_STORAGE_KEY
            ? JSON.stringify({
                accessToken: "token",
                email: "user@example.com",
              })
            : null,
      },
    });

    expect(resolveInitialRoute("/")).toBe("aktuell");
    vi.unstubAllGlobals();
  });

  it("keeps welcome for guests on the home path", () => {
    vi.stubGlobal("window", {
      sessionStorage: { getItem: () => null },
      localStorage: { getItem: () => null },
    });

    expect(resolveInitialRoute("/")).toBe("willkommen");
    vi.unstubAllGlobals();
  });
});

describe("shouldLandOnAktuell", () => {
  it("redirects only authenticated users with a saved profile from welcome", () => {
    expect(shouldLandOnAktuell("willkommen", true, true)).toBe(true);
    expect(shouldLandOnAktuell("willkommen", false, true)).toBe(false);
    expect(shouldLandOnAktuell("willkommen", true, false)).toBe(false);
    expect(shouldLandOnAktuell("entdecken", true, true)).toBe(false);
  });
});
