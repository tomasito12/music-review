import { useState } from "react";
import type { FormEvent, ReactElement } from "react";

import { ApiClient } from "../lib/apiClient";
import {
  profileOverwriteConfirmIntro,
  profileOverwriteConfirmKeepLabel,
  profileOverwriteConfirmSaveLabel,
  profileOverwriteConfirmTitle,
  shouldConfirmProfileOverwrite,
} from "../lib/authProfileOverwrite";
import {
  authDialogCssModifier,
  authDialogEyebrow,
  authDialogIntro,
  authDialogSubmitLabel,
  authDialogSwitchAction,
  authDialogSwitchPrompt,
  authDialogTitle,
  shouldShowAuthModeSwitch,
} from "../lib/authDialogCopy";
import {
  authErrorMessage,
  validateLoginForm,
  validateSaveProfileForm,
} from "../lib/authForm";
import type { AuthSession } from "../lib/authSessionStorage";
import {
  fetchSavedTasteProfile,
  loginAccount,
  registerAccount,
  saveTasteProfile,
} from "../lib/plattenradarApi";
import type { TemporaryTasteProfile } from "../lib/plattenradarApi";

type AuthDialogStep = "credentials" | "overwrite-confirm";

interface AuthDialogProps {
  lockMode?: boolean;
  mode: "login" | "save-profile";
  onClose: () => void;
  onSuccess: (session: AuthSession) => void;
  onSwitchMode: (mode: "login" | "save-profile") => void;
  profileToSave?: TemporaryTasteProfile | null;
}

export function AuthDialog({
  lockMode = false,
  mode,
  onClose,
  onSuccess,
  onSwitchMode,
  profileToSave = null,
}: AuthDialogProps): ReactElement {
  const isLogin = mode === "login";
  const [step, setStep] = useState<AuthDialogStep>("credentials");
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [passwordConfirm, setPasswordConfirm] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [submitting, setSubmitting] = useState(false);
  const [pendingSession, setPendingSession] = useState<AuthSession | null>(null);
  const showModeSwitch = shouldShowAuthModeSwitch(lockMode) && step === "credentials";
  const savingProfile = profileToSave !== null;

  function resetOverwriteStep(): void {
    setStep("credentials");
    setPendingSession(null);
  }

  function handleSwitchMode(nextMode: "login" | "save-profile"): void {
    resetOverwriteStep();
    setError(null);
    onSwitchMode(nextMode);
  }

  async function completeLogin(
    session: AuthSession,
    authedClient: ApiClient,
  ): Promise<void> {
    if (profileToSave === null) {
      onSuccess(session);
      return;
    }

    const existingProfile = await fetchSavedTasteProfile(authedClient);
    if (!shouldConfirmProfileOverwrite(existingProfile, profileToSave)) {
      if (existingProfile === null) {
        await saveTasteProfile(authedClient, profileToSave);
      }
      onSuccess(session);
      return;
    }

    setPendingSession(session);
    setStep("overwrite-confirm");
  }

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
      const session = {
        accessToken: result.token,
        email: result.user.email,
      };
      if (!isLogin) {
        onSuccess(session);
        return;
      }

      const authedClient = new ApiClient({ token: result.token });
      await completeLogin(session, authedClient);
    } catch (caught) {
      setError(authErrorMessage(caught, mode));
    } finally {
      setSubmitting(false);
    }
  }

  async function handleOverwriteConfirm(): Promise<void> {
    if (pendingSession === null || profileToSave === null) {
      return;
    }
    setSubmitting(true);
    setError(null);
    try {
      const authedClient = new ApiClient({ token: pendingSession.accessToken });
      await saveTasteProfile(authedClient, profileToSave);
      onSuccess(pendingSession);
    } catch (caught) {
      setError(authErrorMessage(caught, mode));
    } finally {
      setSubmitting(false);
    }
  }

  function handleKeepExistingProfile(): void {
    if (pendingSession === null) {
      return;
    }
    onSuccess(pendingSession);
  }

  if (step === "overwrite-confirm") {
    return (
      <div className="dialog-backdrop" onClick={onClose} role="presentation">
        <section
          aria-modal="true"
          className={`auth-dialog auth-dialog--overwrite ${authDialogCssModifier(mode)}`}
          onClick={(event) => event.stopPropagation()}
          role="dialog"
        >
          <button className="dialog-close" onClick={onClose} type="button">
            Schließen
          </button>
          <p className="eyebrow">Anmeldung</p>
          <h1>{profileOverwriteConfirmTitle}</h1>
          <p className="auth-dialog-warning">{profileOverwriteConfirmIntro}</p>
          {error !== null && <p className="form-error">{error}</p>}
          <div className="auth-dialog-form auth-dialog-form--actions">
            <button
              className="primary-button"
              disabled={submitting}
              onClick={() => void handleOverwriteConfirm()}
              type="button"
            >
              {submitting ? "Bitte warten ..." : profileOverwriteConfirmSaveLabel}
            </button>
            <button
              className="secondary-button"
              disabled={submitting}
              onClick={handleKeepExistingProfile}
              type="button"
            >
              {profileOverwriteConfirmKeepLabel}
            </button>
          </div>
        </section>
      </div>
    );
  }

  return (
    <div className="dialog-backdrop" onClick={onClose} role="presentation">
      <section
        aria-modal="true"
        className={`auth-dialog ${authDialogCssModifier(mode)}`}
        onClick={(event) => event.stopPropagation()}
        role="dialog"
      >
        <button className="dialog-close" onClick={onClose} type="button">
          Schließen
        </button>
        <p className="eyebrow">{authDialogEyebrow(mode)}</p>
        <h1>{authDialogTitle(mode)}</h1>
        <p>{authDialogIntro(mode, savingProfile)}</p>
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
            {submitting ? "Bitte warten ..." : authDialogSubmitLabel(mode, savingProfile)}
          </button>
        </form>
        {showModeSwitch && (
          <p className="auth-dialog-switch">
            {authDialogSwitchPrompt(mode)}{" "}
            <button
              className="text-button"
              onClick={() => handleSwitchMode(isLogin ? "save-profile" : "login")}
              type="button"
            >
              {authDialogSwitchAction(mode)}
            </button>
          </p>
        )}
      </section>
    </div>
  );
}
