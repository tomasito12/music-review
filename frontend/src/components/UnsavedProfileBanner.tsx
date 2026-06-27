import type { ReactElement } from "react";

import type { ProfileSaveBannerState } from "../lib/unsavedProfileBanner";

interface UnsavedProfileBannerProps {
  state: ProfileSaveBannerState;
  onSave: () => void;
}

export function UnsavedProfileBanner({
  state,
  onSave,
}: UnsavedProfileBannerProps): ReactElement | null {
  if (!state.visible) {
    return null;
  }

  return (
    <aside
      aria-live="polite"
      className={`profile-save-banner profile-save-banner--${state.variant}`}
      data-variant={state.variant}
    >
      <p className="profile-save-banner-message">{state.message}</p>
      {state.showSaveButton && (
        <button className="secondary-button" onClick={onSave} type="button">
          Speichern
        </button>
      )}
    </aside>
  );
}
