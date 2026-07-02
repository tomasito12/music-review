import { describe, expect, it } from "vitest";

import {
  archiveAlbumLimitBounds,
  archivePoolChipLimits,
  archivePoolSummary,
  clampArchiveAlbumLimit,
  clampTrackCount,
  defaultArchiveAlbumLimit,
  playlistSourceContextLine,
  trackCountHint,
} from "./playlistForm";

describe("archiveAlbumLimitBounds", () => {
  it("uses the full pool when fewer than 20 albums match", () => {
    expect(archiveAlbumLimitBounds(12)).toEqual({ min: 1, max: 12 });
  });

  it("starts at 20 for larger pools", () => {
    expect(archiveAlbumLimitBounds(347)).toEqual({ min: 20, max: 347 });
  });
});

describe("defaultArchiveAlbumLimit", () => {
  it("caps at 200 albums by default", () => {
    expect(defaultArchiveAlbumLimit(347)).toBe(200);
    expect(defaultArchiveAlbumLimit(45)).toBe(45);
  });
});

describe("archivePoolChipLimits", () => {
  it("includes relative chips and the full pool", () => {
    expect(archivePoolChipLimits(347)).toEqual([50, 200, 347]);
    expect(archivePoolChipLimits(120)).toEqual([50, 120]);
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
    expect(archivePoolSummary(347, 200)).toBe(
      "347 Alben passen zu deinem Profil — Playlist aus den Top 200.",
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

describe("playlistSourceContextLine", () => {
  it("describes newest and archive entry context", () => {
    expect(playlistSourceContextLine("aktuell", "4")).toBe(
      "Aus deinen Neuheiten · Letzte 4 Update-Runden",
    );
    expect(playlistSourceContextLine("entdecken", "1")).toBe(
      "Aus dem Plattentests-Archiv",
    );
  });
});
