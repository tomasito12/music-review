import type { ReactElement } from "react";

import type { ProfileSaveBannerState } from "../lib/unsavedProfileBanner";

interface UnsavedProfileBannerProps {
  state: ProfileSaveBannerState;
  onDiscard: () => void;
  onSave: () => void;
}

export function UnsavedProfileBanner({
  state,
  onDiscard,
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
      {(state.showSaveButton || state.showDiscardButton) && (
        <div className="profile-save-banner-actions">
          {state.showDiscardButton && (
            <button className="ghost-button" onClick={onDiscard} type="button">
              Änderungen verwerfen
            </button>
          )}
          {state.showSaveButton && (
            <button className="secondary-button" onClick={onSave} type="button">
              Speichern
            </button>
          )}
        </div>
      )}
    </aside>
  );
}
