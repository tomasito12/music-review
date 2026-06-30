import { render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";

import { HighlightAccentPanel } from "./HighlightAccentPanel";

describe("HighlightAccentPanel", () => {
  it("shows rating and fit summary in the accent panel", () => {
    render(<HighlightAccentPanel fitLabel="Sehr passend" fitPercent={88} rating={9} />);

    expect(screen.getByText("9")).toBeTruthy();
    expect(screen.getByText("/10")).toBeTruthy();
    expect(screen.getByText("88%")).toBeTruthy();
    expect(screen.getByText("Sehr passend")).toBeTruthy();
  });
});
