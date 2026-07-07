// @vitest-environment jsdom

import { afterEach, describe, expect, it } from "vitest";

import { createTemporaryTasteProfile } from "./plattenradarApi";
import {
  buildPlaylistExportPayload,
  bumpPlaylistNameSuffix,
  defaultPlaylistNameForSource,
  playlistApiSource,
  playlistItemsToCsv,
  playlistItemsToTxt,
  playlistNameForExportDownload,
  playlistTxtFilename,
  stripPlaylistNameSuffix,
  suggestedPlaylistExportFilename,
  tasteSettingsForArchiveSpread,
  tasteSettingsForNewest,
} from "./playlistExport";

describe("playlistApiSource", () => {
  it("maps UI sources to API playlist sources", () => {
    expect(playlistApiSource("entdecken")).toBe("archive");
    expect(playlistApiSource("aktuell")).toBe("new_reviews");
  });
});

describe("defaultPlaylistNameForSource", () => {
  afterEach(() => {
    delete document.documentElement.dataset.visualTest;
  });

  it("uses mode-specific labels", () => {
    const date = new Date("2026-07-02T12:00:00.000Z");

    expect(defaultPlaylistNameForSource("aktuell", date)).toBe("Plattenradar 2026-07-02");
    expect(defaultPlaylistNameForSource("entdecken", date)).toBe(
      "Plattenarchiv 2026-07-02",
    );
  });
});

describe("stripPlaylistNameSuffix", () => {
  it("removes a trailing numeric suffix", () => {
    expect(stripPlaylistNameSuffix("Plattenradar 2026-07-02 (2)")).toBe(
      "Plattenradar 2026-07-02",
    );
  });
});

describe("playlistNameForExportDownload", () => {
  it("keeps the base name on the first export", () => {
    expect(playlistNameForExportDownload("Plattenradar 2026-07-02", 1)).toBe(
      "Plattenradar 2026-07-02",
    );
  });

  it("adds numeric suffixes only from the second export onward", () => {
    expect(playlistNameForExportDownload("Plattenradar 2026-07-02", 2)).toBe(
      "Plattenradar 2026-07-02 (2)",
    );
    expect(playlistNameForExportDownload("Plattenradar 2026-07-02", 3)).toBe(
      "Plattenradar 2026-07-02 (3)",
    );
  });

  it("uses a fixed reference date during visual regression", () => {
    document.documentElement.dataset.visualTest = "true";

    expect(defaultPlaylistNameForSource("aktuell")).toBe("Plattenradar 2026-06-27");
    expect(defaultPlaylistNameForSource("entdecken")).toBe(
      "Plattenarchiv 2026-06-27",
    );
  });
});

describe("bumpPlaylistNameSuffix", () => {
  it("appends (2) on the first remix", () => {
    expect(bumpPlaylistNameSuffix("Plattenradar 2026-07-02")).toBe(
      "Plattenradar 2026-07-02 (2)",
    );
  });

  it("increments an existing numeric suffix", () => {
    expect(bumpPlaylistNameSuffix("Plattenarchiv 2026-07-02 (2)")).toBe(
      "Plattenarchiv 2026-07-02 (3)",
    );
  });
});

describe("tasteSettingsForNewest", () => {
  it("favors exploration at the low end", () => {
    expect(tasteSettingsForNewest(0)).toEqual({
      tasteExponent: 1,
      selectionStrategy: "stratified",
    });
  });

  it("favors focused playlists at the high end", () => {
    expect(tasteSettingsForNewest(1)).toEqual({
      tasteExponent: 3,
      selectionStrategy: "stratified",
    });
  });

  it("uses stratified selection for mid-range focus", () => {
    expect(tasteSettingsForNewest(0.5)).toEqual({
      tasteExponent: 2,
      selectionStrategy: "stratified",
    });
  });
});

describe("tasteSettingsForArchiveSpread", () => {
  it("maps spread presets to API weighting parameters", () => {
    expect(tasteSettingsForArchiveSpread("variety")).toEqual({
      tasteExponent: 1,
      selectionStrategy: "weighted_sample",
    });
    expect(tasteSettingsForArchiveSpread("balanced")).toEqual({
      tasteExponent: 1.7,
      selectionStrategy: "weighted_sample",
    });
    expect(tasteSettingsForArchiveSpread("deep")).toEqual({
      tasteExponent: 3,
      selectionStrategy: "stratified",
    });
  });
});

describe("buildPlaylistExportPayload", () => {
  it("includes archive pool and spread settings for entdecken", () => {
    const payload = buildPlaylistExportPayload({
      source: "entdecken",
      profile: createTemporaryTasteProfile(["C001"]),
      name: "Meine Liste",
      targetCount: 25,
      newestTasteFocus: 0,
      archiveSpread: "variety",
      archiveAlbumLimit: 120,
      updateRounds: "4",
      format: "csv",
    });

    expect(payload.source).toBe("archive");
    expect(payload.target_count).toBe(25);
    expect(payload.selection_strategy).toBe("weighted_sample");
    expect(payload.archive_limit).toBe(120);
    expect(payload.taste_exponent).toBe(1);
    expect(payload.album_spread_mode).toBe("variety");
    expect(payload.format).toBe("csv");
  });

  it("clamps archive_limit to the API maximum", () => {
    const payload = buildPlaylistExportPayload({
      source: "entdecken",
      profile: createTemporaryTasteProfile(["C001"]),
      name: "Großes Archiv",
      targetCount: 30,
      newestTasteFocus: 0,
      archiveSpread: "balanced",
      archiveAlbumLimit: 6236,
      updateRounds: "1",
      format: "csv",
    });

    expect(payload.archive_limit).toBe(1000);
  });

  it("uses update rounds and newest taste settings for aktuell", () => {
    const payload = buildPlaylistExportPayload({
      source: "aktuell",
      profile: createTemporaryTasteProfile(["C001"]),
      name: "Neu",
      targetCount: 10,
      newestTasteFocus: 1,
      archiveSpread: "balanced",
      archiveAlbumLimit: 200,
      updateRounds: "4",
      format: "csv",
    });

    expect(payload.source).toBe("new_reviews");
    expect(payload.update_rounds).toBe(4);
    expect(payload.taste_exponent).toBe(3);
    expect(payload.selection_strategy).toBe("stratified");
    expect(payload.album_spread_mode).toBeUndefined();
  });

  it("falls back to a mode-specific default playlist name", () => {
    const payload = buildPlaylistExportPayload({
      source: "entdecken",
      profile: createTemporaryTasteProfile(["C001"]),
      name: "   ",
      targetCount: 10,
      newestTasteFocus: 0,
      archiveSpread: "balanced",
      archiveAlbumLimit: 50,
      updateRounds: "1",
      format: "csv",
    });

    expect(payload.playlist_name).toMatch(/^Plattenarchiv \d{4}-\d{2}-\d{2}$/);
  });
});

describe("playlistItemsToCsv", () => {
  it("includes the playlist name in each row", () => {
    const csv = playlistItemsToCsv(
      [
        {
          review_id: 1,
          artist: "Alpha",
          album: "Album",
          track_title: "Song",
          source_kind: "archive",
          score_weight: 1,
          raw_score: 0.8,
        },
      ],
      "Plattenarchiv 2026-07-02",
    );

    expect(csv).toBe(
      "Track name,Artist name,Playlist name\nSong,Alpha,Plattenarchiv 2026-07-02",
    );
  });
});

describe("suggestedPlaylistExportFilename", () => {
  it("builds a safe filename from the playlist name", () => {
    expect(suggestedPlaylistExportFilename("Plattenarchiv 2026-07-02", ".csv")).toBe(
      "Plattenarchiv-2026-07-02.csv",
    );
  });
});

describe("playlistItemsToTxt", () => {
  it("formats artist-title lines for TuneMyMusic", () => {
    const txt = playlistItemsToTxt([
      {
        review_id: 1,
        artist: "Alpha",
        album: "Album",
        track_title: "Song",
        source_kind: "archive",
        score_weight: 1,
        raw_score: 0.8,
      },
    ]);

    expect(txt).toBe("Alpha - Song");
  });

  it("deduplicates repeated artist-title pairs", () => {
    const txt = playlistItemsToTxt([
      {
        review_id: 1,
        artist: "Alpha",
        album: "Album A",
        track_title: "Song",
        source_kind: "archive",
        score_weight: 1,
        raw_score: 0.8,
      },
      {
        review_id: 2,
        artist: "Alpha",
        album: "Album B",
        track_title: "Song",
        source_kind: "archive",
        score_weight: 1,
        raw_score: 0.7,
      },
    ]);

    expect(txt).toBe("Alpha - Song");
  });
});

describe("playlistTxtFilename", () => {
  it("replaces a csv extension with txt", () => {
    expect(playlistTxtFilename("Meine-Playlist.csv")).toBe("Meine-Playlist.txt");
  });
});
