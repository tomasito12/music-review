import { describe, expect, it } from "vitest";

import { ApiError } from "./apiClient";
import {
  authErrorMessage,
  validateLoginForm,
  validateSaveProfileForm,
} from "./authForm";

describe("authForm", () => {
  it("maps duplicate registration to a login hint", () => {
    expect(
      authErrorMessage(new ApiError("Conflict", 409), "save-profile"),
    ).toContain("bereits registriert");
  });

  it("validates save-profile passwords", () => {
    expect(validateSaveProfileForm("a@b.de", "short", "short")).toContain(
      "8 Zeichen",
    );
    expect(validateSaveProfileForm("a@b.de", "longenough", "different")).toContain(
      "stimmen nicht",
    );
    expect(validateSaveProfileForm("a@b.de", "longenough", "longenough")).toBeNull();
  });

  it("validates login form fields", () => {
    expect(validateLoginForm("", "secret")).toContain("E-Mail");
    expect(validateLoginForm("a@b.de", "")).toContain("Passwort");
    expect(validateLoginForm("a@b.de", "secret")).toBeNull();
  });
});
