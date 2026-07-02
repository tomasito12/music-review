import { describe, expect, it } from "vitest";

import { createTemporaryTasteProfile } from "./plattenradarApi";
import {
  buildPlaylistExportPayload,
  playlistApiSource,
  playlistItemsToCsv,
  tasteSettingsForArchive,
  tasteSettingsForNewest,
} from "./playlistExport";

describe("playlistApiSource", () => {
  it("maps UI sources to API playlist sources", () => {
    expect(playlistApiSource("entdecken")).toBe("archive");
    expect(playlistApiSource("aktuell")).toBe("new_reviews");
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
      selectionStrategy: "weighted_sample",
    });
  });
});

describe("tasteSettingsForArchive", () => {
  it("favors broad spread at the low end", () => {
    expect(tasteSettingsForArchive(0)).toEqual({
      tasteExponent: 1,
      selectionStrategy: "weighted_sample",
    });
  });

  it("favors album depth at the high end", () => {
    expect(tasteSettingsForArchive(1)).toEqual({
      tasteExponent: 3,
      selectionStrategy: "stratified",
    });
  });
});

describe("buildPlaylistExportPayload", () => {
  it("includes archive pool and depth settings for entdecken", () => {
    const payload = buildPlaylistExportPayload({
      source: "entdecken",
      profile: createTemporaryTasteProfile(["C001"]),
      name: "Meine Liste",
      targetCount: 25,
      newestTasteFocus: 0,
      archiveDepth: 0.2,
      archiveAlbumLimit: 120,
      updateRounds: "4",
      format: "txt",
    });

    expect(payload.source).toBe("archive");
    expect(payload.target_count).toBe(25);
    expect(payload.selection_strategy).toBe("weighted_sample");
    expect(payload.archive_limit).toBe(120);
    expect(payload.taste_exponent).toBe(1.4);
  });

  it("uses update rounds and newest taste settings for aktuell", () => {
    const payload = buildPlaylistExportPayload({
      source: "aktuell",
      profile: createTemporaryTasteProfile(["C001"]),
      name: "Neu",
      targetCount: 10,
      newestTasteFocus: 1,
      archiveDepth: 0,
      archiveAlbumLimit: 200,
      updateRounds: "4",
      format: "txt",
    });

    expect(payload.source).toBe("new_reviews");
    expect(payload.update_rounds).toBe(4);
    expect(payload.taste_exponent).toBe(3);
    expect(payload.selection_strategy).toBe("weighted_sample");
  });
});

describe("playlistItemsToCsv", () => {
  it("escapes commas in csv fields", () => {
    const csv = playlistItemsToCsv([
      {
        review_id: 1,
        artist: "A, B",
        album: "Album",
        track_title: "Song",
        source_kind: "archive",
        score_weight: 1,
        raw_score: 0.8,
      },
    ]);

    expect(csv).toContain('"A, B"');
  });
});
