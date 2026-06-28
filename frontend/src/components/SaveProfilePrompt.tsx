import type { ReactElement } from "react";

interface SaveProfilePromptProps {
  onDismiss: () => void;
  onSave: () => void;
}

export function SaveProfilePrompt({
  onDismiss,
  onSave,
}: SaveProfilePromptProps): ReactElement {
  return (
    <aside aria-label="Profil speichern" className="save-profile-prompt">
      <div>
        <strong>Dieses Musikprofil speichern?</strong>
        <p>
          Dann bekommst du beim nächsten Besuch direkt neue Empfehlungen, ohne
          alles neu auszuwählen.
        </p>
      </div>
      <div className="save-profile-prompt-actions">
        <button className="primary-button" onClick={onSave} type="button">
          Profil speichern
        </button>
        <button className="ghost-button" onClick={onDismiss} type="button">
          Später
        </button>
      </div>
    </aside>
  );
}
