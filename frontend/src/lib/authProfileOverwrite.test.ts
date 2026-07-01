import { describe, expect, it } from "vitest";

import { shouldConfirmProfileOverwrite } from "./authProfileOverwrite";
import { createTemporaryTasteProfile } from "./plattenradarApi";

describe("shouldConfirmProfileOverwrite", () => {
  it("returns false when no session profile is present", () => {
    expect(shouldConfirmProfileOverwrite(createTemporaryTasteProfile(["C001"]), null)).toBe(
      false,
    );
  });

  it("returns false when the account has no saved profile yet", () => {
    expect(
      shouldConfirmProfileOverwrite(null, createTemporaryTasteProfile(["C001"])),
    ).toBe(false);
  });

  it("returns false when session and account profiles match", () => {
    const profile = createTemporaryTasteProfile(["C001"]);
    expect(shouldConfirmProfileOverwrite(profile, profile)).toBe(false);
  });

  it("returns true when the session profile differs from the account profile", () => {
    const existing = createTemporaryTasteProfile(["C001"]);
    const session = createTemporaryTasteProfile(["C002"]);
    expect(shouldConfirmProfileOverwrite(existing, session)).toBe(true);
  });
});
