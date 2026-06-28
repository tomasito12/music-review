export const AUTH_SESSION_STORAGE_KEY = "plattenradar.auth-session.v1";
export const SAVE_PROMPT_DISMISSED_KEY = "plattenradar.save-prompt-dismissed.v1";

export interface AuthSession {
  accessToken: string;
  email: string;
}

/** Reads the persisted auth session from local storage. */
export function readAuthSession(): AuthSession | null {
  if (typeof window === "undefined") {
    return null;
  }
  const raw = window.localStorage.getItem(AUTH_SESSION_STORAGE_KEY);
  if (raw === null) {
    return null;
  }
  try {
    const parsed: unknown = JSON.parse(raw);
    if (
      typeof parsed !== "object" ||
      parsed === null ||
      typeof (parsed as AuthSession).accessToken !== "string" ||
      typeof (parsed as AuthSession).email !== "string"
    ) {
      return null;
    }
    return parsed as AuthSession;
  } catch {
    return null;
  }
}

/** Persists the auth session for returning visits. */
export function writeAuthSession(session: AuthSession): void {
  if (typeof window === "undefined") {
    return;
  }
  window.localStorage.setItem(AUTH_SESSION_STORAGE_KEY, JSON.stringify(session));
}

/** Clears the stored auth session. */
export function clearAuthSession(): void {
  if (typeof window === "undefined") {
    return;
  }
  window.localStorage.removeItem(AUTH_SESSION_STORAGE_KEY);
}

/** Returns whether the save prompt was dismissed for this browser tab. */
export function isSavePromptDismissed(): boolean {
  if (typeof window === "undefined") {
    return false;
  }
  return window.sessionStorage.getItem(SAVE_PROMPT_DISMISSED_KEY) === "1";
}

/** Hides the save prompt for the rest of the current browser tab. */
export function dismissSavePrompt(): void {
  if (typeof window === "undefined") {
    return;
  }
  window.sessionStorage.setItem(SAVE_PROMPT_DISMISSED_KEY, "1");
}
