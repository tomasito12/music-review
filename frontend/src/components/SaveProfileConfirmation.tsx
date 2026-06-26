import type { ReactElement } from "react";

interface SaveProfileConfirmationProps {
  email: string;
  onGoToAktuell: () => void;
}

export function SaveProfileConfirmation({
  email,
  onGoToAktuell,
}: SaveProfileConfirmationProps): ReactElement {
  return (
    <aside aria-live="polite" className="save-profile-confirmation">
      <div>
        <strong>Profil gespeichert</strong>
        <p>
          Dein Musikprofil ist jetzt mit {email} verknüpft. Du bleibst in deiner
          aktuellen Auswahl.
        </p>
      </div>
      <button className="secondary-button" onClick={onGoToAktuell} type="button">
        Zu Aktuell wechseln
      </button>
    </aside>
  );
}
