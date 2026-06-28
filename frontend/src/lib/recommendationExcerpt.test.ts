import { describe, expect, it } from "vitest";

import {
  buildExcerptPreview,
  normalizeExcerptText,
} from "./recommendationExcerpt";

describe("normalizeExcerptText", () => {
  it("collapses whitespace", () => {
    expect(normalizeExcerptText("  Hallo   Welt ")).toBe("Hallo Welt");
  });

  it("repairs broken en dashes before normalizing whitespace", () => {
    expect(normalizeExcerptText("  ausgeschieden \u0096   blo\u00df  ")).toBe(
      "ausgeschieden \u2013 blo\u00df",
    );
  });
});

describe("buildExcerptPreview", () => {
  it("returns short text unchanged", () => {
    expect(buildExcerptPreview("Kurzer Text.", () => true)).toBe("Kurzer Text.");
  });

  it("adds a preview marker only when the text does not fit", () => {
    const longText =
      "Dies ist ein sehr langer Rezensionstext der erst nach drei vollen Zeilen abgeschnitten werden soll.";

    const preview = buildExcerptPreview(longText, (candidate) => candidate.length <= 42);

    expect(preview.endsWith("[...]")).toBe(true);
    expect(preview).not.toMatch(/\s\w+\[\.\.\.\]$/);
  });

  it("keeps the longest fitting prefix on a word boundary", () => {
    const preview = buildExcerptPreview(
      "Alpha Beta Gamma Delta Epsilon Zeta",
      (candidate) => candidate.length <= "Alpha Beta Gamma [...]".length,
    );

    expect(preview).toBe("Alpha Beta Gamma [...]");
  });

  it("handles empty input", () => {
    expect(buildExcerptPreview("   ", () => true)).toBe("");
  });

  it("adds a preview marker when the source continues even if the text fits", () => {
    const preview = buildExcerptPreview("Kurzer aber unvollständiger Auszug", () => true, {
      continues: true,
    });

    expect(preview).toBe("Kurzer aber unvollständiger Auszug [...]");
  });

  it("shortens continued text until the preview marker fits", () => {
    const preview = buildExcerptPreview(
      "Alpha Beta Gamma Delta Epsilon Zeta",
      (candidate) => candidate.length <= "Alpha Beta Gamma [...]".length,
      { continues: true },
    );

    expect(preview).toBe("Alpha Beta Gamma [...]");
  });
});
