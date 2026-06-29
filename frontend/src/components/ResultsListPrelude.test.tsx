import { render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";

import { ResultsListPrelude } from "./ResultsListPrelude";

describe("ResultsListPrelude", () => {
  it("renders source-specific tuning copy for Aktuell", () => {
    render(
      <ResultsListPrelude
        filterRegion={<p>Filterbereich</p>}
        source="aktuell"
      />,
    );

    expect(screen.getByRole("heading", { name: "Liste verfeinern" })).toBeTruthy();
    expect(screen.getByText(/die Highlights oben bleiben/i)).toBeTruthy();
    expect(screen.getByText("Filterbereich")).toBeTruthy();
  });

  it("renders source-specific tuning copy for Entdecken", () => {
    render(
      <ResultsListPrelude
        filterRegion={<p>Filterbereich</p>}
        source="entdecken"
      />,
    );

    expect(screen.getByText(/die vier Fundstücke oben bleiben/i)).toBeTruthy();
  });
});
