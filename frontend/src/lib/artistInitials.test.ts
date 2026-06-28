import { describe, expect, it } from "vitest";

import { artistInitials } from "./artistInitials";

describe("artistInitials", () => {
  it("returns two initials for multi-word names", () => {
    expect(artistInitials("Kinderzimmer Productions")).toBe("KP");
  });

  it("returns up to two letters for single-word names", () => {
    expect(artistInitials("Radiohead")).toBe("RA");
  });

  it("returns a fallback for empty names", () => {
    expect(artistInitials("   ")).toBe("?");
  });
});
