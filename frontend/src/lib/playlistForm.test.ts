import { describe, expect, it } from "vitest";

import {
  archiveAlbumLimitBounds,
  archivePoolChipLabel,
  archivePoolChipLimits,
  archivePoolSummary,
  archiveSpreadHint,
  clampArchiveAlbumLimit,
  clampTrackCount,
  defaultArchiveAlbumLimit,
  newestMoodHint,
  newestMoodToTasteFocus,
  isNewestMoodPresetSelected,
  normalizePlaylistUpdateRounds,
  playlistSourceContextLine,
  playlistSuccessHeadline,
  playlistUpdateRoundLabel,
  playlistUpdateRoundPoolHint,
  trackCountHint,
} from "./playlistForm";

describe("archiveAlbumLimitBounds", () => {
  it("uses the full pool when fewer than 20 albums match", () => {
    expect(archiveAlbumLimitBounds(12)).toEqual({ min: 1, max: 12 });
  });

  it("starts at 20 for larger pools", () => {
    expect(archiveAlbumLimitBounds(347)).toEqual({ min: 20, max: 347 });
  });

  it("caps the slider at the API archive limit", () => {
    expect(archiveAlbumLimitBounds(6236)).toEqual({ min: 20, max: 6236 });
  });
});

describe("defaultArchiveAlbumLimit", () => {
  it("caps at 100 albums by default", () => {
    expect(defaultArchiveAlbumLimit(347)).toBe(100);
    expect(defaultArchiveAlbumLimit(45)).toBe(45);
  });
});

describe("archivePoolChipLimits", () => {
  it("includes relative chips and the full pool", () => {
    expect(archivePoolChipLimits(347)).toEqual([50, 100, 250, 347]);
    expect(archivePoolChipLimits(120)).toEqual([50, 100, 120]);
  });

  it("caps the largest chip at the full matching pool", () => {
    expect(archivePoolChipLimits(6236)).toEqual([50, 100, 250, 500, 750, 6236]);
  });
});

describe("clampArchiveAlbumLimit", () => {
  it("clamps values into the pool range", () => {
    expect(clampArchiveAlbumLimit(347, 999)).toBe(347);
    expect(clampArchiveAlbumLimit(347, 12)).toBe(20);
  });
});

describe("archivePoolSummary", () => {
  it("describes the personalized archive pool", () => {
    expect(archivePoolSummary(347, 100)).toBe(
      "347 Alben passen zu deinem Profil — Playlist aus den Top 100.",
    );
  });

  it("describes very large pools with optional technical cap", () => {
    expect(archivePoolSummary(25000, 20000)).toContain("technisches Maximum");
  });

  it("offers all albums when the pool fits within the API cap", () => {
    expect(archivePoolSummary(5341, 5341)).toBe(
      "5.341 Alben passen zu deinem Profil — Playlist aus allen.",
    );
  });
});

describe("clampTrackCount", () => {
  it("keeps track counts inside the supported range", () => {
    expect(clampTrackCount(3)).toBe(5);
    expect(clampTrackCount(30)).toBe(30);
    expect(clampTrackCount(120)).toBe(100);
  });
});

describe("trackCountHint", () => {
  it("returns short helper copy for presets", () => {
    expect(trackCountHint(30)).toBe("30 Titel — gut zum Reinhören");
    expect(trackCountHint(50)).toBe("50 Titel — längere Hörsession");
  });
});

describe("archivePoolChipLabel", () => {
  it("labels the full pool chip as Alle", () => {
    expect(archivePoolChipLabel(5341, 5341, 5341)).toBe("Alle");
  });

  it("returns numeric labels for intermediate chips", () => {
    expect(archivePoolChipLabel(250, 5341, 5341)).toBe("250");
  });
});

describe("playlistSuccessHeadline", () => {
  it("describes newest and archive results", () => {
    expect(playlistSuccessHeadline("aktuell", 30)).toBe(
      "Deine Playlist ist fertig — 30 Titel aus deinen Neuheiten.",
    );
    expect(playlistSuccessHeadline("entdecken", 12)).toBe(
      "Deine Playlist ist fertig — 12 Titel aus Entdecken.",
    );
  });
});

describe("archiveSpreadHint", () => {
  it("returns track-count-aware helper copy for archive spread presets", () => {
    expect(archiveSpreadHint("variety", 50)).toContain("50 Alben");
    expect(archiveSpreadHint("deep", 50)).toContain("Top 2–3");
  });
});

describe("playlistUpdateRoundLabel", () => {
  it("labels single and multi-round windows", () => {
    expect(playlistUpdateRoundLabel(1)).toBe("Letzte Runde");
    expect(playlistUpdateRoundLabel(4)).toBe("Letzte 4");
  });
});

describe("normalizePlaylistUpdateRounds", () => {
  it("keeps supported values and snaps unknown values", () => {
    expect(normalizePlaylistUpdateRounds("8")).toBe("8");
    expect(normalizePlaylistUpdateRounds("3")).toBe("2");
  });
});

describe("isNewestMoodPresetSelected", () => {
  it("matches preset taste-focus values within a small tolerance", () => {
    expect(isNewestMoodPresetSelected(0.25, "balanced")).toBe(true);
    expect(isNewestMoodPresetSelected(0.4, "balanced")).toBe(false);
  });
});

describe("newestMoodToTasteFocus", () => {
  it("maps presets to taste focus values aligned with Streamlit exponents", () => {
    expect(newestMoodToTasteFocus("variety")).toBe(0);
    expect(newestMoodToTasteFocus("balanced")).toBe(0.5);
    expect(newestMoodToTasteFocus("focused")).toBe(1);
  });
});

describe("newestMoodHint", () => {
  it("returns helper copy for each preset", () => {
    expect(newestMoodHint("variety")).toContain("zusätzlich");
    expect(newestMoodHint("focused")).toContain("Titel pro Album");
  });
});

describe("playlistUpdateRoundPoolHint", () => {
  it("describes batch history and fallback pool sizing", () => {
    expect(playlistUpdateRoundPoolHint("1")).toContain("exakt");
    expect(playlistUpdateRoundPoolHint("4")).toContain("geschätzt ~80");
  });
});

describe("playlistSourceContextLine", () => {
  it("describes newest and archive entry context", () => {
    expect(playlistSourceContextLine("aktuell", "4")).toBe(
      "Aus deinen Neuheiten · Letzte 4",
    );
    expect(playlistSourceContextLine("entdecken", "1")).toBe(
      "Aus dem Plattentests-Archiv",
    );
  });
});
