import { useEffect, useState } from "react";

import { ApiClient } from "../lib/apiClient";
import {
  loadTasteCommunities,
  loadTastePresets,
} from "../lib/plattenradarApi";
import type { TasteCommunityOption, TastePreset } from "../lib/plattenradarApi";

interface ResultsFilterOptionsState {
  communities: TasteCommunityOption[];
  error: string | null;
  loading: boolean;
  presets: TastePreset[];
}

/** Loads presets and communities for inline result-page filter controls. */
export function useResultsFilterOptions(enabled: boolean): ResultsFilterOptionsState {
  const [presets, setPresets] = useState<TastePreset[]>([]);
  const [communities, setCommunities] = useState<TasteCommunityOption[]>([]);
  const [loading, setLoading] = useState(enabled);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    if (!enabled) {
      return;
    }

    let active = true;

    async function loadOptions(): Promise<void> {
      const client = new ApiClient();
      try {
        const [presetOptions, communityOptions] = await Promise.all([
          loadTastePresets(client),
          loadTasteCommunities(client),
        ]);
        if (!active) {
          return;
        }
        setPresets(presetOptions);
        setCommunities(communityOptions);
        setError(null);
      } catch {
        if (active) {
          setError(
            "Filter-Einstellungen konnten gerade nicht geladen werden. Bitte versuche es noch einmal.",
          );
        }
      } finally {
        if (active) {
          setLoading(false);
        }
      }
    }

    void loadOptions();
    return () => {
      active = false;
    };
  }, [enabled]);

  return { communities, error, loading, presets };
}
