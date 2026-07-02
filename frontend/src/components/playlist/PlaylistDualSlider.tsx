import type { ReactElement } from "react";

interface PlaylistDualSliderProps {
  ariaLabel: string;
  leftLabel: string;
  onChange: (value: number) => void;
  rightLabel: string;
  value: number;
}

/** Two-ended slider with labels for playlist taste controls. */
export function PlaylistDualSlider({
  ariaLabel,
  leftLabel,
  onChange,
  rightLabel,
  value,
}: PlaylistDualSliderProps): ReactElement {
  const clamped = Math.min(1, Math.max(0, value));

  return (
    <div className="playlist-dual-slider">
      <div className="playlist-dual-slider-labels">
        <span>{leftLabel}</span>
        <span>{rightLabel}</span>
      </div>
      <input
        aria-label={ariaLabel}
        aria-valuetext={`${Math.round(clamped * 100)} Prozent Richtung ${rightLabel}`}
        className="playlist-dual-slider-input"
        max={1}
        min={0}
        onChange={(event) => {
          onChange(Number(event.target.value));
        }}
        step={0.05}
        type="range"
        value={clamped}
      />
    </div>
  );
}
