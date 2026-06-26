import { useState } from "react";
import type { FormEvent, ReactElement } from "react";

import { ApiClient } from "../lib/apiClient";
import {
  authErrorMessage,
  validateLoginForm,
  validateSaveProfileForm,
} from "../lib/authForm";
import type { AuthSession } from "../lib/authSessionStorage";
import { loginAccount, registerAccount, saveTasteProfile } from "../lib/plattenradarApi";
import type { TemporaryTasteProfile } from "../lib/plattenradarApi";

interface AuthDialogProps {
  mode: "login" | "save-profile";
  onClose: () => void;
  onSuccess: (session: AuthSession) => void;
  onSwitchMode: (mode: "login" | "save-profile") => void;
  profileToSave?: TemporaryTasteProfile | null;
}

export function AuthDialog({
  mode,
  onClose,
  onSuccess,
  onSwitchMode,
  profileToSave = null,
}: AuthDialogProps): ReactElement {
  const isLogin = mode === "login";
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [passwordConfirm, setPasswordConfirm] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [submitting, setSubmitting] = useState(false);

  async function handleSubmit(event: FormEvent<HTMLFormElement>): Promise<void> {
    event.preventDefault();
    const validationError = isLogin
      ? validateLoginForm(email, password)
      : validateSaveProfileForm(email, password, passwordConfirm);
    if (validationError !== null) {
      setError(validationError);
      return;
    }
    if (!isLogin && profileToSave === null) {
      setError("Es ist kein Musikprofil zum Speichern vorhanden.");
      return;
    }

    setSubmitting(true);
    setError(null);
    const client = new ApiClient();
    try {
      const result = isLogin
        ? await loginAccount(client, email.trim(), password)
        : await registerAccount(
            client,
            email.trim(),
            password,
            profileToSave ?? undefined,
          );
      if (isLogin && profileToSave !== null) {
        const authedClient = new ApiClient({ token: result.token });
        await saveTasteProfile(authedClient, profileToSave);
      }
      onSuccess({
        accessToken: result.token,
        email: result.user.email,
      });
    } catch (caught) {
      setError(authErrorMessage(caught, mode));
    } finally {
      setSubmitting(false);
    }
  }

  return (
    <div className="dialog-backdrop" onClick={onClose} role="presentation">
      <section
        aria-modal="true"
        className="auth-dialog"
        onClick={(event) => event.stopPropagation()}
        role="dialog"
      >
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
        <form className="auth-dialog-form" onSubmit={handleSubmit}>
          <label>
            E-Mail
            <input
              autoComplete="email"
              onChange={(event) => setEmail(event.target.value)}
              placeholder="du@example.com"
              type="email"
              value={email}
            />
          </label>
          <label>
            Passwort
            <input
              autoComplete={isLogin ? "current-password" : "new-password"}
              onChange={(event) => setPassword(event.target.value)}
              type="password"
              value={password}
            />
          </label>
          {!isLogin && (
            <label>
              Passwort bestätigen
              <input
                autoComplete="new-password"
                onChange={(event) => setPasswordConfirm(event.target.value)}
                type="password"
                value={passwordConfirm}
              />
            </label>
          )}
          {error !== null && <p className="form-error">{error}</p>}
          <button className="primary-button" disabled={submitting} type="submit">
            {submitting
              ? "Bitte warten ..."
              : isLogin
                ? "Einloggen"
                : "Profil speichern"}
          </button>
        </form>
        <p className="auth-dialog-switch">
          {isLogin ? (
            <>
              Noch kein Konto?{" "}
              <button
                className="text-button"
                onClick={() => onSwitchMode("save-profile")}
                type="button"
              >
                Profil speichern
              </button>
            </>
          ) : (
            <>
              Bereits ein Konto?{" "}
              <button
                className="text-button"
                onClick={() => onSwitchMode("login")}
                type="button"
              >
                Einloggen
              </button>
            </>
          )}
        </p>
      </section>
    </div>
  );
}
