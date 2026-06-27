export interface ProfileSaveBannerInput {
  isAuthenticated: boolean;
  hasUnsavedProfileChanges: boolean;
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
    isSavingProfileChanges,
    savedMessage,
    errorMessage,
  } = input;

  if (!isAuthenticated) {
    return { visible: false };
  }

  if (savedMessage !== null && !hasUnsavedProfileChanges && !isSavingProfileChanges) {
    return {
      visible: true,
      variant: "saved",
      message: savedMessage,
      showSaveButton: false,
    };
  }

  if (!hasUnsavedProfileChanges && !isSavingProfileChanges) {
    return { visible: false };
  }

  if (isSavingProfileChanges) {
    return {
      visible: true,
      variant: "saving",
      message: "Speichert ...",
      showSaveButton: false,
    };
  }

  if (errorMessage !== null) {
    return {
      visible: true,
      variant: "error",
      message: errorMessage,
      showSaveButton: true,
    };
  }

  return {
    visible: true,
    variant: "unsaved",
    message: "Profil geändert · noch nicht gespeichert",
    showSaveButton: true,
  };
}
