// @vitest-environment jsdom

import { afterEach, describe, expect, it } from "vitest";

import { isVisualTestMode } from "./visualTestMode";

describe("isVisualTestMode", () => {
  afterEach(() => {
    delete document.documentElement.dataset.visualTest;
  });

  it("returns false when the visual-test dataset flag is absent", () => {
    expect(isVisualTestMode()).toBe(false);
  });

  it("returns true when the visual-test dataset flag is enabled", () => {
    document.documentElement.dataset.visualTest = "true";
    expect(isVisualTestMode()).toBe(true);
  });
});
