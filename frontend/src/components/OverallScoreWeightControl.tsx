import type { ReactElement } from "react";

import { overallWeightQuestion, overallWeightShortLabel } from "../lib/filterControls";
import {
  OVERALL_WEIGHT_FIELDS,
  overallSharePercents,
  updateOverallWeightShare,
  type OverallWeightField,
} from "../lib/overallWeightControls";
import type { TasteFilterSettings } from "../lib/plattenradarApi";
import {
  handleCommittedRangeKeyUp,
  useCommittedRangeValue,
  type SliderApplyMode,
} from "../lib/useCommittedRangeValue";

interface OverallScoreWeightControlProps {
  applyMode: SliderApplyMode;
  filterSettings: TasteFilterSettings;
  onChange: (settings: TasteFilterSettings) => void;
}

const SEGMENT_CLASS_NAMES = [
  "overall-weight-segment--alpha",
  "overall-weight-segment--beta",
  "overall-weight-segment--gamma",
] as const;

function ShareSlider({
  applyMode,
  field,
  filterSettings,
  onChange,
  sharePercent,
}: {
  applyMode: SliderApplyMode;
  field: OverallWeightField;
  filterSettings: TasteFilterSettings;
  onChange: (settings: TasteFilterSettings) => void;
  sharePercent: number;
}): ReactElement {
  const { displayValue, onRangeChange, onRangeCommit } = useCommittedRangeValue(
    sharePercent,
    (nextValue) => {
      onChange(updateOverallWeightShare(filterSettings, field, nextValue));
    },
    applyMode,
  );

  return (
    <label className="overall-weight-row" key={field}>
      <span className="overall-weight-question">{overallWeightQuestion(field)}</span>
      <div className="overall-weight-row-controls">
        <input
          aria-valuetext={`Anteil ${displayValue} Prozent`}
          className="overall-weight-share-input"
          max={100}
          min={0}
          onChange={(event) => {
            onRangeChange(Number(event.target.value));
          }}
          onKeyUp={(event) => {
            handleCommittedRangeKeyUp(event, onRangeCommit);
          }}
          onPointerUp={onRangeCommit}
          onTouchEnd={onRangeCommit}
          step={5}
          type="range"
          value={displayValue}
        />
        <span className="overall-weight-share-value">{displayValue} %</span>
      </div>
    </label>
  );
}

/** Three-way score weighting that always presents shares summing to 100 %. */
export function OverallScoreWeightControl({
  applyMode,
  filterSettings,
  onChange,
}: OverallScoreWeightControlProps): ReactElement {
  const sharePercents = overallSharePercents(filterSettings);

  return (
    <div className="overall-weight-control">
      <p className="field-hint">
        Anteile am Gesamtscore — zusammen immer 100 %. Höhere Anteile ziehen die
        Sortierung stärker in diese Richtung.
      </p>
      <div
        aria-label="Gewichtung des Gesamtscores"
        className="overall-weight-stack"
        role="img"
      >
        {OVERALL_WEIGHT_FIELDS.map((field, index) => (
          <div
            className={`overall-weight-segment ${SEGMENT_CLASS_NAMES[index]}`}
            key={field}
            style={{ width: `${sharePercents[index]}%` }}
            title={`${overallWeightShortLabel(field)}: ${sharePercents[index]} %`}
          />
        ))}
      </div>
      <div aria-hidden="true" className="overall-weight-stack-labels">
        {OVERALL_WEIGHT_FIELDS.map((field, index) => (
          <span key={field}>
            {overallWeightShortLabel(field)}: {sharePercents[index]} %
          </span>
        ))}
      </div>
      <div className="overall-weight-sliders">
        {OVERALL_WEIGHT_FIELDS.map((field, index) => (
          <ShareSlider
            applyMode={applyMode}
            field={field}
            filterSettings={filterSettings}
            key={field}
            onChange={onChange}
            sharePercent={sharePercents[index]}
          />
        ))}
      </div>
    </div>
  );
}
