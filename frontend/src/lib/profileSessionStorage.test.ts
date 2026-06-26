import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

import { createTemporaryTasteProfile } from "./plattenradarApi";
import {
  PROFILE_SESSION_STORAGE_KEY,
  buildFilterSummaryChips,
  clearProfileSession,
  readProfileSession,
  writeProfileSession,
} from "./profileSessionStorage";

const sampleSession = {
  presetId: "precise",
  presetLabel: "Treffsicher",
  profile: createTemporaryTasteProfile(["C001", "C002", "C003"]),
};

function installSessionStorageMock(): void {
  const store = new Map<string, string>();
  vi.stubGlobal("window", {
    sessionStorage: {
      getItem: (key: string) => store.get(key) ?? null,
      setItem: (key: string, value: string) => {
        store.set(key, value);
      },
      removeItem: (key: string) => {
        store.delete(key);
      },
    },
  });
}

beforeEach(() => {
  installSessionStorageMock();
});

afterEach(() => {
  clearProfileSession();
  vi.unstubAllGlobals();
});

describe("profileSessionStorage", () => {
  it("returns null when no session is stored", () => {
    expect(readProfileSession()).toBeNull();
  });

  it("round-trips a profile session through session storage", () => {
    writeProfileSession(sampleSession);
    const restored = readProfileSession();

    expect(restored?.presetId).toBe("precise");
    expect(restored?.presetLabel).toBe("Treffsicher");
    expect(restored?.profile.selected_communities).toEqual(["C001", "C002", "C003"]);
  });

  it("returns null for malformed session payloads", () => {
    window.sessionStorage.setItem(
      PROFILE_SESSION_STORAGE_KEY,
      JSON.stringify({ presetId: "broken" }),
    );

    expect(readProfileSession()).toBeNull();
  });

  it("builds filter summary chips from the stored session", () => {
    expect(buildFilterSummaryChips(sampleSession)).toEqual([
      "Treffsicher",
      "3 Detailstile",
      "Wertung 6–10",
    ]);
  });
});
