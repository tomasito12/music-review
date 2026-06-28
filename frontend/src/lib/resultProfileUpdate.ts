import {
  createTemporaryTasteProfile,
  filterSettingsFromPreset,
} from "./plattenradarApi";
import type { TasteFilterSettings, TastePreset } from "./plattenradarApi";
import type { ProfileSetupResult } from "./profileSessionStorage";

export interface ProfileSessionUpdate {
  presetId?: string;
  presetLabel?: string;
  filterSettings?: TasteFilterSettings;
  communityWeightsRaw?: Record<string, number>;
}

/** Merges filter or preset changes into the active profile session. */
export function buildUpdatedProfileSession(
  session: ProfileSetupResult,
  update: ProfileSessionUpdate,
): ProfileSetupResult {
  const filterSettings =
    update.filterSettings ?? session.profile.filter_settings;
  const communityWeightsRaw =
    update.communityWeightsRaw ?? session.profile.community_weights_raw;

  return {
    presetId: update.presetId ?? session.presetId,
    presetLabel: update.presetLabel ?? session.presetLabel,
    profile: createTemporaryTasteProfile(
      session.profile.selected_communities,
      filterSettings,
      communityWeightsRaw,
    ),
  };
}

/** Applies a preset selection to the active profile session. */
export function buildProfileSessionFromPreset(
  session: ProfileSetupResult,
  preset: TastePreset,
): ProfileSetupResult {
  return buildUpdatedProfileSession(session, {
    presetId: preset.id,
    presetLabel: preset.label,
    filterSettings: filterSettingsFromPreset(preset),
  });
}
