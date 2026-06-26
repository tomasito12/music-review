import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

import {
  AUTH_SESSION_STORAGE_KEY,
  SAVE_PROMPT_DISMISSED_KEY,
  clearAuthSession,
  dismissSavePrompt,
  isSavePromptDismissed,
  readAuthSession,
  writeAuthSession,
} from "./authSessionStorage";

function installStorageMocks(): void {
  const localStore = new Map<string, string>();
  const sessionStore = new Map<string, string>();
  vi.stubGlobal("window", {
    localStorage: {
      getItem: (key: string) => localStore.get(key) ?? null,
      setItem: (key: string, value: string) => {
        localStore.set(key, value);
      },
      removeItem: (key: string) => {
        localStore.delete(key);
      },
    },
    sessionStorage: {
      getItem: (key: string) => sessionStore.get(key) ?? null,
      setItem: (key: string, value: string) => {
        sessionStore.set(key, value);
      },
      removeItem: (key: string) => {
        sessionStore.delete(key);
      },
    },
  });
}

beforeEach(() => {
  installStorageMocks();
});

afterEach(() => {
  clearAuthSession();
  vi.unstubAllGlobals();
});

describe("authSessionStorage", () => {
  it("round-trips the auth session through local storage", () => {
    writeAuthSession({ accessToken: "token-1", email: "alice@example.com" });

    expect(readAuthSession()).toEqual({
      accessToken: "token-1",
      email: "alice@example.com",
    });
  });

  it("tracks save prompt dismissal per browser tab", () => {
    expect(isSavePromptDismissed()).toBe(false);
    dismissSavePrompt();
    expect(isSavePromptDismissed()).toBe(true);
    expect(window.sessionStorage.getItem(SAVE_PROMPT_DISMISSED_KEY)).toBe("1");
  });

  it("returns null for malformed auth payloads", () => {
    window.localStorage.setItem(
      AUTH_SESSION_STORAGE_KEY,
      JSON.stringify({ accessToken: "only-token" }),
    );

    expect(readAuthSession()).toBeNull();
  });
});
