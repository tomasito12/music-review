import { describe, expect, it } from "vitest";

import { createTemporaryTasteProfile } from "./plattenradarApi";
import {
  buildPlaylistExportPayload,
  playlistApiSource,
  playlistItemsToCsv,
  playlistSelectionStrategy,
  playlistTasteExponent,
} from "./playlistExport";

describe("playlistApiSource", () => {
  it("maps UI sources to API playlist sources", () => {
    expect(playlistApiSource("entdecken")).toBe("archive");
    expect(playlistApiSource("aktuell")).toBe("new_reviews");
  });
});

describe("playlistSelectionStrategy", () => {
  it("uses stratified for balanced newest playlists", () => {
    expect(playlistSelectionStrategy("aktuell", "balanced")).toBe("stratified");
  });

  it("uses weighted sampling for archive and top-focus playlists", () => {
    expect(playlistSelectionStrategy("entdecken", "balanced")).toBe("weighted_sample");
    expect(playlistSelectionStrategy("aktuell", "top")).toBe("weighted_sample");
  });
});

describe("buildPlaylistExportPayload", () => {
  it("includes profile and archive settings for entdecken", () => {
    const payload = buildPlaylistExportPayload({
      source: "entdecken",
      profile: createTemporaryTasteProfile(["C001"]),
      name: "Meine Liste",
      targetCount: 25,
      focus: "balanced",
      variation: 0.35,
      updateRounds: "4",
      format: "txt",
    });

    expect(payload.source).toBe("archive");
    expect(payload.target_count).toBe(25);
    expect(payload.selection_strategy).toBe("weighted_sample");
    expect(payload.archive_limit).toBe(200);
  });

  it("uses update rounds for newest playlist exports", () => {
    const payload = buildPlaylistExportPayload({
      source: "aktuell",
      profile: createTemporaryTasteProfile(["C001"]),
      name: "Neu",
      targetCount: 10,
      focus: "top",
      variation: 0,
      updateRounds: "4",
      format: "txt",
    });

    expect(payload.source).toBe("new_reviews");
    expect(payload.update_rounds).toBe(4);
    expect(payload.taste_exponent).toBe(3);
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

describe("playlistTasteExponent", () => {
  it("increases with variation for balanced playlists", () => {
    expect(playlistTasteExponent("balanced", 0)).toBe(1);
    expect(playlistTasteExponent("balanced", 0.5)).toBe(2);
  });
});
