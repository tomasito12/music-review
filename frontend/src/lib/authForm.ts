import { ApiError } from "./apiClient";

/** Returns a German user-facing message for auth form failures. */
export function authErrorMessage(
  error: unknown,
  mode: "login" | "save-profile",
): string {
  if (error instanceof ApiError) {
    if (error.status === 409 && mode === "save-profile") {
      return "Diese E-Mail ist bereits registriert. Bitte logge dich ein.";
    }
    if (error.status === 401) {
      return "E-Mail oder Passwort stimmen nicht.";
    }
    if (error.status === 422) {
      return "Bitte gib eine gültige E-Mail-Adresse ein.";
    }
  }
  return "Die Anmeldung ist gerade nicht möglich. Bitte versuche es später erneut.";
}

/** Validates save-profile form input before calling the API. */
export function validateSaveProfileForm(
  email: string,
  password: string,
  passwordConfirm: string,
): string | null {
  if (email.trim() === "") {
    return "Bitte gib deine E-Mail-Adresse ein.";
  }
  if (password.length < 8) {
    return "Das Passwort muss mindestens 8 Zeichen lang sein.";
  }
  if (password !== passwordConfirm) {
    return "Die Passwörter stimmen nicht überein.";
  }
  return null;
}

/** Validates login form input before calling the API. */
export function validateLoginForm(email: string, password: string): string | null {
  if (email.trim() === "") {
    return "Bitte gib deine E-Mail-Adresse ein.";
  }
  if (password === "") {
    return "Bitte gib dein Passwort ein.";
  }
  return null;
}
