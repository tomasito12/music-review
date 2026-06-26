import { describe, expect, it } from "vitest";

import { balanceFillPercents, snapBalanceValue } from "./balanceSlider";

describe("balanceFillPercents", () => {
  it("fills only to the left below neutral", () => {
    expect(balanceFillPercents(-0.5)).toEqual({ left: 25, right: 0 });
  });

  it("fills only to the right above neutral", () => {
    expect(balanceFillPercents(1)).toEqual({ left: 0, right: 50 });
  });

  it("stays empty at the center null point", () => {
    expect(balanceFillPercents(0)).toEqual({ left: 0, right: 0 });
  });
});

describe("snapBalanceValue", () => {
  it("snaps to the configured step within bounds", () => {
    expect(snapBalanceValue(0.34)).toBe(0.3);
    expect(snapBalanceValue(5)).toBe(1);
  });
});
