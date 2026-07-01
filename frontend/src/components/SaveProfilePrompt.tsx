import type { ReactElement } from "react";

interface SaveProfilePromptProps {
  onCreateAccount: () => void;
  onDismiss: () => void;
  onSaveToExistingAccount: () => void;
}

export function SaveProfilePrompt({
  onCreateAccount,
  onDismiss,
  onSaveToExistingAccount,
}: SaveProfilePromptProps): ReactElement {
  return (
    <aside aria-label="Profil speichern" className="save-profile-prompt">
      <div>
        <strong>Dieses Musikprofil speichern?</strong>
        <p>
          Lege ein neues Konto an oder melde dich an, um dein aktuelles Profil in
          deinem bestehenden Konto zu sichern.
        </p>
      </div>
      <div className="save-profile-prompt-actions">
        <button className="primary-button" onClick={onSaveToExistingAccount} type="button">
          In bestehendes Konto speichern
        </button>
        <button className="secondary-button" onClick={onCreateAccount} type="button">
          Konto anlegen
        </button>
        <button className="ghost-button" onClick={onDismiss} type="button">
          Später
        </button>
      </div>
    </aside>
  );
}
