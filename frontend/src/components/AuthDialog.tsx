import type { ReactElement } from "react";

interface AuthDialogProps {
  mode: "login" | "save-profile";
  onClose: () => void;
}

export function AuthDialog({ mode, onClose }: AuthDialogProps): ReactElement {
  const isLogin = mode === "login";

  return (
    <div className="dialog-backdrop" role="presentation">
      <section aria-modal="true" className="auth-dialog" role="dialog">
        <button className="dialog-close" onClick={onClose} type="button">
          Schließen
        </button>
        <p className="eyebrow">{isLogin ? "Einloggen" : "Profil speichern"}</p>
        <h1>{isLogin ? "Mit deinem Profil fortfahren" : "Profil per E-Mail sichern"}</h1>
        <p>
          {isLogin
            ? "Melde dich mit E-Mail und Passwort an, damit Plattenradar dein gespeichertes Musikprofil laden kann."
            : "Speichere dein aktuelles Musikprofil, damit du beim nächsten Besuch direkt neue Empfehlungen siehst."}
        </p>
        <label>
          E-Mail
          <input placeholder="du@example.com" type="email" />
        </label>
        <label>
          Passwort
          <input type="password" />
        </label>
        <button className="primary-button" type="button">
          {isLogin ? "Einloggen" : "Profil speichern"}
        </button>
      </section>
    </div>
  );
}
