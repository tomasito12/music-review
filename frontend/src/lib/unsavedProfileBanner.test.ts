import { describe, expect, it } from "vitest";

import { resolveProfileSaveBannerState } from "./unsavedProfileBanner";

const baseInput = {
  isAuthenticated: true,
  hasUnsavedProfileChanges: false,
  needsInitialAccountSave: false,
  isSavingProfileChanges: false,
  savedMessage: null,
  errorMessage: null,
};

describe("resolveProfileSaveBannerState", () => {
  it("hides the banner for guests", () => {
    expect(
      resolveProfileSaveBannerState({
        ...baseInput,
        isAuthenticated: false,
        hasUnsavedProfileChanges: true,
      }),
    ).toEqual({ visible: false });
  });

  it("shows an unsaved state with a save action", () => {
    expect(
      resolveProfileSaveBannerState({
        ...baseInput,
        hasUnsavedProfileChanges: true,
      }),
    ).toEqual({
      visible: true,
      variant: "unsaved",
      message: "Profil geändert · noch nicht gespeichert",
      showSaveButton: true,
      showDiscardButton: true,
    });
  });

  it("shows a first-save state without discard for logged-in users", () => {
    expect(
      resolveProfileSaveBannerState({
        ...baseInput,
        needsInitialAccountSave: true,
      }),
    ).toEqual({
      visible: true,
      variant: "unsaved",
      message: "Profil noch nicht in deinem Konto gespeichert",
      showSaveButton: true,
      showDiscardButton: false,
    });
  });

  it("shows a saving state without a save action", () => {
    expect(
      resolveProfileSaveBannerState({
        ...baseInput,
        hasUnsavedProfileChanges: true,
        isSavingProfileChanges: true,
      }),
    ).toEqual({
      visible: true,
      variant: "saving",
      message: "Speichert ...",
      showSaveButton: false,
      showDiscardButton: false,
    });
  });

  it("shows a short saved confirmation after saving", () => {
    expect(
      resolveProfileSaveBannerState({
        ...baseInput,
        savedMessage: "Gespeichert.",
      }),
    ).toEqual({
      visible: true,
      variant: "saved",
      message: "Gespeichert.",
      showSaveButton: false,
      showDiscardButton: false,
    });
  });

  it("prefers the error state when saving failed", () => {
    expect(
      resolveProfileSaveBannerState({
        ...baseInput,
        hasUnsavedProfileChanges: true,
        errorMessage: "Speichern fehlgeschlagen.",
      }),
    ).toEqual({
      visible: true,
      variant: "error",
      message: "Speichern fehlgeschlagen.",
      showSaveButton: true,
      showDiscardButton: true,
    });
  });
});
