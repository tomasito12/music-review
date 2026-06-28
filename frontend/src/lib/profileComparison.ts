import { temporaryProfileToApi } from "./plattenradarApi";
import type { TemporaryTasteProfile } from "./plattenradarApi";

/** Returns true when two profiles would serialize to the same API payload. */
export function tasteProfilesMatch(
  left: TemporaryTasteProfile,
  right: TemporaryTasteProfile,
): boolean {
  return (
    JSON.stringify(temporaryProfileToApi(left)) ===
    JSON.stringify(temporaryProfileToApi(right))
  );
}

/** Creates a detached copy for tracking the last saved server profile. */
export function cloneTasteProfile(profile: TemporaryTasteProfile): TemporaryTasteProfile {
  return {
    name: profile.name,
    selected_communities: [...profile.selected_communities],
    community_weights_raw: { ...profile.community_weights_raw },
    filter_settings: { ...profile.filter_settings },
  };
}
