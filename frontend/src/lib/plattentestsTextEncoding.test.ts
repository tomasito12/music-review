import { describe, expect, it } from "vitest";

import { repairPlattentestsText } from "./plattentestsTextEncoding";

describe("repairPlattentestsText", () => {
  it("replaces C1 control U+0096 with an en dash", () => {
    const broken = "ausgeschieden \u0096 blo\u00df zwei Jahre";
    expect(repairPlattentestsText(broken)).toBe("ausgeschieden \u2013 blo\u00df zwei Jahre");
  });

  it("replaces em dash and curly quotes", () => {
    const broken = "\u0097 \u0093Lighthouse\u0094";
    expect(repairPlattentestsText(broken)).toBe("\u2014 \u201cLighthouse\u201d");
  });

  it("leaves already-correct UTF-8 unchanged", () => {
    const clean = "Sch\u00f6n \u2013 bereits korrekt.";
    expect(repairPlattentestsText(clean)).toBe(clean);
  });

  it("returns empty strings unchanged", () => {
    expect(repairPlattentestsText("")).toBe("");
  });
});
