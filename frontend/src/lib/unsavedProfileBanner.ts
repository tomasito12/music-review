export interface ProfileSaveBannerInput {
  isAuthenticated: boolean;
  hasUnsavedProfileChanges: boolean;
  needsInitialAccountSave: boolean;
  isSavingProfileChanges: boolean;
  savedMessage: string | null;
  errorMessage: string | null;
}

export type ProfileSaveBannerVariant = "unsaved" | "saving" | "saved" | "error";

export interface ProfileSaveBannerView {
  visible: true;
  variant: ProfileSaveBannerVariant;
  message: string;
  showSaveButton: boolean;
  showDiscardButton: boolean;
}

export type ProfileSaveBannerState =
  | { visible: false }
  | ProfileSaveBannerView;

/** Decide whether the global profile-save banner should appear and how. */
export function resolveProfileSaveBannerState(
  input: ProfileSaveBannerInput,
): ProfileSaveBannerState {
  const {
    isAuthenticated,
    hasUnsavedProfileChanges,
    needsInitialAccountSave,
    isSavingProfileChanges,
    savedMessage,
    errorMessage,
  } = input;

  const hasPendingProfileSave = hasUnsavedProfileChanges || needsInitialAccountSave;

  if (!isAuthenticated) {
    return { visible: false };
  }

  if (savedMessage !== null && !hasPendingProfileSave && !isSavingProfileChanges) {
    return {
      visible: true,
      variant: "saved",
      message: savedMessage,
      showSaveButton: false,
      showDiscardButton: false,
    };
  }

  if (!hasPendingProfileSave && !isSavingProfileChanges) {
    return { visible: false };
  }

  if (isSavingProfileChanges) {
    return {
      visible: true,
      variant: "saving",
      message: "Speichert ...",
      showSaveButton: false,
      showDiscardButton: false,
    };
  }

  if (errorMessage !== null) {
    return {
      visible: true,
      variant: "error",
      message: errorMessage,
      showSaveButton: true,
      showDiscardButton: true,
    };
  }

  return {
    visible: true,
    variant: "unsaved",
    message: needsInitialAccountSave
      ? "Profil noch nicht in deinem Konto gespeichert"
      : "Profil geändert · noch nicht gespeichert",
    showSaveButton: true,
    showDiscardButton: hasUnsavedProfileChanges,
  };
}
