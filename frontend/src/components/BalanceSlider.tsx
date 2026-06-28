import type { ReactElement } from "react";

import { balanceFillPercents, snapBalanceValue } from "../lib/balanceSlider";
import {
  handleCommittedRangeKeyUp,
  useCommittedRangeValue,
  type SliderApplyMode,
} from "../lib/useCommittedRangeValue";

interface BalanceSliderProps {
  applyMode?: SliderApplyMode;
  ariaLabel: string;
  max?: number;
  min?: number;
  onChange: (value: number) => void;
  step?: number;
  value: number;
}

/** Stereo-style balance control with a visible center null point. */
export function BalanceSlider({
  applyMode = "immediate",
  ariaLabel,
  max = 1,
  min = -1,
  onChange,
  step = 0.1,
  value,
}: BalanceSliderProps): ReactElement {
  const { displayValue, onRangeChange, onRangeCommit } = useCommittedRangeValue(
    value,
    onChange,
    applyMode,
  );
  const clamped = snapBalanceValue(displayValue, step, min, max);
  const { left, right } = balanceFillPercents(clamped, min, max);

  return (
    <div
      className="balance-slider"
      onDoubleClick={() => {
        onChange(0);
      }}
      title="Doppelklick setzt auf neutral"
    >
      <div aria-hidden="true" className="balance-slider-track">
        <div
          className="balance-slider-fill balance-slider-fill--left"
          style={{ width: `${left}%` }}
        />
        <div
          className="balance-slider-fill balance-slider-fill--right"
          style={{ width: `${right}%` }}
        />
        <div className="balance-slider-center" />
      </div>
      <input
        aria-label={ariaLabel}
        aria-valuetext={
          clamped === 0
            ? "Neutral"
            : clamped < 0
              ? `${Math.round(Math.abs(clamped * 100))} Prozent schwächer`
              : `${Math.round(clamped * 100)} Prozent stärker`
        }
        className="balance-slider-input"
        max={max}
        min={min}
        onChange={(event) => {
          onRangeChange(
            snapBalanceValue(Number(event.target.value), step, min, max),
          );
        }}
        onKeyUp={(event) => {
          handleCommittedRangeKeyUp(event, onRangeCommit);
        }}
        onPointerUp={onRangeCommit}
        onTouchEnd={onRangeCommit}
        step={step}
        type="range"
        value={clamped}
      />
    </div>
  );
}
