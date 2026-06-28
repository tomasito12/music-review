import { useCallback, useEffect, useState } from "react";
import type { KeyboardEvent } from "react";

export type SliderApplyMode = "immediate" | "commit";

const RANGE_COMMIT_KEYS = new Set([
  "ArrowDown",
  "ArrowLeft",
  "ArrowRight",
  "ArrowUp",
  "End",
  "Home",
]);

/** Return whether a keyboard event should commit a range edit. */
export function shouldCommitCommittedRangeKey(key: string): boolean {
  return RANGE_COMMIT_KEYS.has(key);
}

/** Resolve display and commit behavior for one range input change. */
export function resolveCommittedRangeChange(
  applyMode: SliderApplyMode,
  externalValue: number,
  draftValue: number,
  nextValue: number,
): {
  commitValue?: number;
  displayValue: number;
  nextDraftValue: number;
} {
  if (applyMode === "immediate") {
    return {
      commitValue: nextValue,
      displayValue: externalValue,
      nextDraftValue: draftValue,
    };
  }
  return {
    displayValue: nextValue,
    nextDraftValue: nextValue,
  };
}

/** Resolve the value to commit when the user releases a range control. */
export function resolveCommittedRangeCommit(
  applyMode: SliderApplyMode,
  draftValue: number,
): number | undefined {
  if (applyMode === "immediate") {
    return undefined;
  }
  return draftValue;
}

interface CommittedRangeValueState {
  displayValue: number;
  onRangeChange: (nextValue: number) => void;
  onRangeCommit: () => void;
}

/** Range slider state that can apply immediately or only after pointer release. */
export function useCommittedRangeValue(
  value: number,
  onCommit: (nextValue: number) => void,
  applyMode: SliderApplyMode,
): CommittedRangeValueState {
  const [draftValue, setDraftValue] = useState(value);

  useEffect(() => {
    setDraftValue(value);
  }, [value]);

  const onRangeChange = useCallback(
    (nextValue: number) => {
      const resolved = resolveCommittedRangeChange(
        applyMode,
        value,
        draftValue,
        nextValue,
      );
      if (resolved.commitValue !== undefined) {
        onCommit(resolved.commitValue);
        return;
      }
      setDraftValue(resolved.nextDraftValue);
    },
    [applyMode, draftValue, onCommit, value],
  );

  const onRangeCommit = useCallback(() => {
    const commitValue = resolveCommittedRangeCommit(applyMode, draftValue);
    if (commitValue === undefined) {
      return;
    }
    onCommit(commitValue);
  }, [applyMode, draftValue, onCommit]);

  return {
    displayValue:
      applyMode === "immediate" ? value : draftValue,
    onRangeChange,
    onRangeCommit,
  };
}

/** Keyboard handler that commits range edits after arrow-key adjustments. */
export function handleCommittedRangeKeyUp(
  event: KeyboardEvent<HTMLInputElement>,
  onRangeCommit: () => void,
): void {
  if (shouldCommitCommittedRangeKey(event.key)) {
    onRangeCommit();
  }
}
