import {
  migrateLegacyCommunityWeights,
  normalizeCommunityWeights,
} from "./communityWeightMapping";
import { normalizeFilterSettings } from "./plattenradarApi";
import type { TemporaryTasteProfile } from "./plattenradarApi";

export const PROFILE_SESSION_STORAGE_KEY = "plattenradar.profile-session.v1";

export interface ProfileSetupResult {
  presetId: string;
  presetLabel: string;
  profile: TemporaryTasteProfile;
}

export interface StoredProfileSession extends ProfileSetupResult {
  savedAt: string;
}

/** Reads the temporary profile session from session storage. */
export function readProfileSession(): StoredProfileSession | null {
  if (typeof window === "undefined") {
    return null;
  }
  const raw = window.sessionStorage.getItem(PROFILE_SESSION_STORAGE_KEY);
  if (raw === null) {
    return null;
  }
  try {
    const parsed: unknown = JSON.parse(raw);
    return normalizeStoredProfileSession(parsed);
  } catch {
    return null;
  }
}

/** Persists the temporary profile session for the current browser tab. */
export function writeProfileSession(session: ProfileSetupResult): void {
  if (typeof window === "undefined") {
    return;
  }
  const payload: StoredProfileSession = {
    ...session,
    savedAt: new Date().toISOString(),
  };
  window.sessionStorage.setItem(
    PROFILE_SESSION_STORAGE_KEY,
    JSON.stringify(payload),
  );
}

/** Removes any stored temporary profile session. */
export function clearProfileSession(): void {
  if (typeof window === "undefined") {
    return;
  }
  window.sessionStorage.removeItem(PROFILE_SESSION_STORAGE_KEY);
}

/** Builds compact filter-summary chips for the results toolbar. */
export function buildFilterSummaryChips(
  session: ProfileSetupResult,
): string[] {
  const { filter_settings: filters } = session.profile;
  return [
    session.presetLabel,
    `${session.profile.selected_communities.length} Detailstile`,
    `Wertung ${filters.rating_min}–${filters.rating_max}`,
  ];
}

function normalizeStoredProfileSession(value: unknown): StoredProfileSession | null {
  if (typeof value !== "object" || value === null) {
    return null;
  }
  const record = value as Record<string, unknown>;
  const profile = record.profile;
  const presetId = record.presetId;
  const presetLabel = record.presetLabel;
  const savedAt = record.savedAt;
  if (
    typeof presetId !== "string" ||
    typeof presetLabel !== "string" ||
    typeof savedAt !== "string" ||
    !isTemporaryProfile(profile)
  ) {
    return null;
  }
  return {
    presetId,
    presetLabel,
    profile: {
      ...profile,
      community_weights_raw: migrateLegacyCommunityWeights(
        normalizeCommunityWeights(
          profile.selected_communities,
          profile.community_weights_raw,
        ),
      ),
      filter_settings: normalizeFilterSettings(profile.filter_settings),
    },
    savedAt,
  };
}

function isTemporaryProfile(value: unknown): value is TemporaryTasteProfile {
  if (typeof value !== "object" || value === null) {
    return false;
  }
  const record = value as Record<string, unknown>;
  return (
    typeof record.name === "string" &&
    Array.isArray(record.selected_communities) &&
    record.selected_communities.every((item) => typeof item === "string") &&
    typeof record.community_weights_raw === "object" &&
    record.community_weights_raw !== null &&
    typeof record.filter_settings === "object" &&
    record.filter_settings !== null
  );
}
