export type AuthDialogMode = "login" | "save-profile";

/** Return whether the dialog should offer switching between login and registration. */
export function shouldShowAuthModeSwitch(lockMode: boolean): boolean {
  return !lockMode;
}

export function authDialogEyebrow(mode: AuthDialogMode): string {
  return mode === "login" ? "Einloggen" : "Konto anlegen";
}

export function authDialogTitle(mode: AuthDialogMode): string {
  return mode === "login" ? "Anmelden" : "Profil dauerhaft speichern";
}

export function authDialogIntro(mode: AuthDialogMode): string {
  if (mode === "login") {
    return "Melde dich mit E-Mail und Passwort an, damit Plattenradar dein gespeichertes Musikprofil laden kann.";
  }
  return "Lege ein Konto an und sichere dein aktuelles Musikprofil für den nächsten Besuch.";
}

export function authDialogSubmitLabel(mode: AuthDialogMode): string {
  return mode === "login" ? "Einloggen" : "Konto erstellen";
}

export function authDialogSwitchPrompt(mode: AuthDialogMode): string {
  return mode === "login" ? "Noch kein Konto?" : "Schon registriert?";
}

export function authDialogSwitchAction(mode: AuthDialogMode): string {
  return mode === "login" ? "Konto anlegen" : "Anmelden";
}

export function authDialogCssModifier(mode: AuthDialogMode): string {
  return mode === "login" ? "auth-dialog--login" : "auth-dialog--register";
}
