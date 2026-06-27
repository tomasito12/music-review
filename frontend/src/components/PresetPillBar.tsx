import type { ReactElement } from "react";

import type { TastePreset } from "../lib/plattenradarApi";

interface PresetPillBarProps {
  presets: TastePreset[];
  selectedPresetId: string;
  onSelect: (preset: TastePreset) => void;
}

export function PresetPillBar({
  presets,
  selectedPresetId,
  onSelect,
}: PresetPillBarProps): ReactElement {
  return (
    <div aria-label="Musikprofil-Presets" className="results-preset-bar" role="group">
      {presets.map((preset) => (
        <button
          aria-pressed={selectedPresetId === preset.id}
          className="results-preset-pill"
          key={preset.id}
          onClick={() => onSelect(preset)}
          title={preset.subtitle}
          type="button"
        >
          {preset.label}
        </button>
      ))}
    </div>
  );
}
