import { render, screen } from "@testing-library/react";
import { describe, expect, it, vi } from "vitest";

import { SaveProfilePrompt } from "./SaveProfilePrompt";

describe("SaveProfilePrompt", () => {
  it("offers saving to an existing account and creating a new one", () => {
    const onCreateAccount = vi.fn();
    const onDismiss = vi.fn();
    const onSaveToExistingAccount = vi.fn();

    render(
      <SaveProfilePrompt
        onCreateAccount={onCreateAccount}
        onDismiss={onDismiss}
        onSaveToExistingAccount={onSaveToExistingAccount}
      />,
    );

    screen.getByRole("button", { name: "In bestehendes Konto speichern" }).click();
    screen.getByRole("button", { name: "Konto anlegen" }).click();
    screen.getByRole("button", { name: "Später" }).click();

    expect(onSaveToExistingAccount).toHaveBeenCalledTimes(1);
    expect(onCreateAccount).toHaveBeenCalledTimes(1);
    expect(onDismiss).toHaveBeenCalledTimes(1);
  });
});
