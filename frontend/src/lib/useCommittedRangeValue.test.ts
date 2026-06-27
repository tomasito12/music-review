import type { KeyboardEvent } from "react";
import { describe, expect, it, vi } from "vitest";

import {
  handleCommittedRangeKeyUp,
  resolveCommittedRangeChange,
  resolveCommittedRangeCommit,
  shouldCommitCommittedRangeKey,
} from "./useCommittedRangeValue";

describe("resolveCommittedRangeChange", () => {
  it("commits immediately in immediate mode", () => {
    const result = resolveCommittedRangeChange("immediate", 0.5, 0.5, 0.8);
    expect(result.commitValue).toBe(0.8);
    expect(result.displayValue).toBe(0.5);
  });

  it("updates draft only in commit mode", () => {
    const result = resolveCommittedRangeChange("commit", 0.5, 0.5, 0.8);
    expect(result.commitValue).toBeUndefined();
    expect(result.displayValue).toBe(0.8);
    expect(result.nextDraftValue).toBe(0.8);
  });
});

describe("resolveCommittedRangeCommit", () => {
  it("returns draft value in commit mode", () => {
    expect(resolveCommittedRangeCommit("commit", 0.8)).toBe(0.8);
  });

  it("returns undefined in immediate mode", () => {
    expect(resolveCommittedRangeCommit("immediate", 0.8)).toBeUndefined();
  });
});

describe("shouldCommitCommittedRangeKey", () => {
  it("accepts arrow keys", () => {
    expect(shouldCommitCommittedRangeKey("ArrowRight")).toBe(true);
  });

  it("rejects unrelated keys", () => {
    expect(shouldCommitCommittedRangeKey("Enter")).toBe(false);
  });
});

describe("handleCommittedRangeKeyUp", () => {
  it("commits on arrow key release", () => {
    const onRangeCommit = vi.fn();
    handleCommittedRangeKeyUp(
      { key: "ArrowRight" } as KeyboardEvent<HTMLInputElement>,
      onRangeCommit,
    );
    expect(onRangeCommit).toHaveBeenCalledOnce();
  });

  it("ignores unrelated keys", () => {
    const onRangeCommit = vi.fn();
    handleCommittedRangeKeyUp(
      { key: "Enter" } as KeyboardEvent<HTMLInputElement>,
      onRangeCommit,
    );
    expect(onRangeCommit).not.toHaveBeenCalled();
  });
});
