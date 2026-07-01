import type { InputHTMLAttributes, ReactElement } from "react";

import {
  handleCommittedRangeKeyUp,
  useCommittedRangeValue,
  type SliderApplyMode,
} from "../lib/useCommittedRangeValue";

interface ThresholdSliderProps
  extends Omit<InputHTMLAttributes<HTMLInputElement>, "type" | "value" | "onChange"> {
  applyMode: SliderApplyMode;
  formatValue?: (value: number) => string;
  onValueCommit: (value: number) => void;
  rejectedLabel?: string;
  keptLabel?: string;
  value: number;
}

/** Minimum-threshold slider: kept range is to the right of the handle. */
export function ThresholdSlider({
  applyMode,
  formatValue,
  max = 100,
  min = 0,
  onValueCommit,
  rejectedLabel = "Ausgeschlossen",
  keptLabel = "Bleibt sichtbar",
  value,
  ...inputProps
}: ThresholdSliderProps): ReactElement {
  const numericMax = Number(max);
  const numericMin = Number(min);
  const span = Math.max(numericMax - numericMin, 1);
  const { displayValue, onRangeChange, onRangeCommit } = useCommittedRangeValue(
    value,
    onValueCommit,
    applyMode,
  );
  const cutoffPercent = ((displayValue - numericMin) / span) * 100;
  const valueLabel = formatValue?.(displayValue) ?? String(displayValue);

  return (
    <div className="threshold-slider">
      <div className="threshold-slider-hitbox">
        <div aria-hidden="true" className="threshold-slider-track">
          <div
            className="threshold-slider-rejected"
            style={{ width: `${cutoffPercent}%` }}
            title={rejectedLabel}
          />
          <div
            className="threshold-slider-kept"
            style={{
              left: `${cutoffPercent}%`,
              width: `${100 - cutoffPercent}%`,
            }}
            title={keptLabel}
          />
          <div
            className="threshold-slider-marker"
            style={{ left: `${cutoffPercent}%` }}
          />
        </div>
        <input
          aria-valuetext={`Schwellwert ${valueLabel}`}
          className="threshold-slider-input"
          max={max}
          min={min}
          onChange={(event) => {
            onRangeChange(Number(event.target.value));
          }}
          onKeyUp={(event) => {
            handleCommittedRangeKeyUp(event, onRangeCommit);
          }}
          onPointerUp={onRangeCommit}
          onTouchEnd={onRangeCommit}
          type="range"
          value={displayValue}
          {...inputProps}
        />
      </div>
      <div aria-hidden="true" className="threshold-slider-legend">
        <span>{rejectedLabel}</span>
        <span>{keptLabel}</span>
      </div>
    </div>
  );
}
