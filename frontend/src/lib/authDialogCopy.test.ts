import { describe, expect, it } from "vitest";

import {
  authDialogCssModifier,
  authDialogEyebrow,
  authDialogIntro,
  authDialogSubmitLabel,
  authDialogSwitchAction,
  authDialogSwitchPrompt,
  authDialogTitle,
  shouldShowAuthModeSwitch,
} from "./authDialogCopy";

describe("shouldShowAuthModeSwitch", () => {
  it("hides mode switch when entry mode is locked", () => {
    expect(shouldShowAuthModeSwitch(true)).toBe(false);
  });

  it("shows mode switch when entry mode is not locked", () => {
    expect(shouldShowAuthModeSwitch(false)).toBe(true);
  });
});

describe("authDialogCopy", () => {
  it("uses login wording without save-profile phrasing", () => {
    expect(authDialogEyebrow("login")).toBe("Einloggen");
    expect(authDialogTitle("login")).toBe("Anmelden");
    expect(authDialogSubmitLabel("login")).toBe("Einloggen");
    expect(authDialogSwitchAction("login")).toBe("Konto anlegen");
    expect(authDialogSwitchPrompt("login")).toBe("Noch kein Konto?");
  });

  it("uses login wording when saving an existing session profile", () => {
    expect(authDialogIntro("login", true)).toContain("bestehenden Konto");
    expect(authDialogSubmitLabel("login", true)).toBe("Anmelden und speichern");
  });

  it("uses registration wording for save-profile mode", () => {
    expect(authDialogEyebrow("save-profile")).toBe("Konto anlegen");
    expect(authDialogTitle("save-profile")).toBe("Profil dauerhaft speichern");
    expect(authDialogSubmitLabel("save-profile")).toBe("Konto erstellen");
    expect(authDialogSwitchAction("save-profile")).toBe("Anmelden");
    expect(authDialogIntro("save-profile")).toContain("Konto");
  });

  it("maps css modifiers per mode", () => {
    expect(authDialogCssModifier("login")).toBe("auth-dialog--login");
    expect(authDialogCssModifier("save-profile")).toBe("auth-dialog--register");
  });
});
