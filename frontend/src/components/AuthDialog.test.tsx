import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import { describe, expect, it, vi } from "vitest";

import { AuthDialog } from "./AuthDialog";
import { createTemporaryTasteProfile } from "../lib/plattenradarApi";

vi.mock("../lib/plattenradarApi", () => ({
  loginAccount: vi.fn(),
  registerAccount: vi.fn(),
  fetchSavedTasteProfile: vi.fn(),
  saveTasteProfile: vi.fn(),
}));

import {
  fetchSavedTasteProfile,
  loginAccount,
  saveTasteProfile,
} from "../lib/plattenradarApi";

function fillLoginForm(email: string, password: string): void {
  fireEvent.change(screen.getByLabelText("E-Mail"), {
    target: { value: email },
  });
  fireEvent.change(screen.getByLabelText("Passwort"), {
    target: { value: password },
  });
}

describe("AuthDialog", () => {
  it("asks before overwriting an existing account profile on login", async () => {
    const sessionProfile = createTemporaryTasteProfile(["C002"]);
    const existingProfile = createTemporaryTasteProfile(["C001"]);
    const onSuccess = vi.fn();

    vi.mocked(loginAccount).mockResolvedValue({
      token: "token-1",
      user: { email: "user@example.com" },
    });
    vi.mocked(fetchSavedTasteProfile).mockResolvedValue(existingProfile);

    render(
      <AuthDialog
        mode="login"
        onClose={vi.fn()}
        onSuccess={onSuccess}
        onSwitchMode={vi.fn()}
        profileToSave={sessionProfile}
      />,
    );

    fillLoginForm("user@example.com", "secret123");
    fireEvent.click(screen.getByRole("button", { name: "Anmelden und speichern" }));

    expect(
      await screen.findByRole("heading", { name: "Bestehendes Profil überschreiben?" }),
    ).toBeTruthy();
    expect(onSuccess).not.toHaveBeenCalled();
    expect(saveTasteProfile).not.toHaveBeenCalled();
  });

  it("saves the session profile when overwrite is confirmed", async () => {
    const sessionProfile = createTemporaryTasteProfile(["C002"]);
    const existingProfile = createTemporaryTasteProfile(["C001"]);
    const onSuccess = vi.fn();

    vi.mocked(loginAccount).mockResolvedValue({
      token: "token-1",
      user: { email: "user@example.com" },
    });
    vi.mocked(fetchSavedTasteProfile).mockResolvedValue(existingProfile);
    vi.mocked(saveTasteProfile).mockResolvedValue(sessionProfile);

    render(
      <AuthDialog
        mode="login"
        onClose={vi.fn()}
        onSuccess={onSuccess}
        onSwitchMode={vi.fn()}
        profileToSave={sessionProfile}
      />,
    );

    fillLoginForm("user@example.com", "secret123");
    fireEvent.click(screen.getByRole("button", { name: "Anmelden und speichern" }));
    fireEvent.click(
      await screen.findByRole("button", { name: "Aktuelles Profil speichern" }),
    );

    await waitFor(() => {
      expect(saveTasteProfile).toHaveBeenCalledTimes(1);
      expect(onSuccess).toHaveBeenCalledWith({
        accessToken: "token-1",
        email: "user@example.com",
      });
    });
  });

  it("keeps the stored account profile when overwrite is declined", async () => {
    const sessionProfile = createTemporaryTasteProfile(["C002"]);
    const existingProfile = createTemporaryTasteProfile(["C001"]);
    const onSuccess = vi.fn();

    vi.mocked(loginAccount).mockResolvedValue({
      token: "token-1",
      user: { email: "user@example.com" },
    });
    vi.mocked(fetchSavedTasteProfile).mockResolvedValue(existingProfile);

    render(
      <AuthDialog
        mode="login"
        onClose={vi.fn()}
        onSuccess={onSuccess}
        onSwitchMode={vi.fn()}
        profileToSave={sessionProfile}
      />,
    );

    fillLoginForm("user@example.com", "secret123");
    fireEvent.click(screen.getByRole("button", { name: "Anmelden und speichern" }));
    fireEvent.click(
      await screen.findByRole("button", { name: "Gespeichertes Profil behalten" }),
    );

    expect(onSuccess).toHaveBeenCalledWith({
      accessToken: "token-1",
      email: "user@example.com",
    });
    expect(saveTasteProfile).not.toHaveBeenCalled();
  });

  it("saves immediately when the account has no stored profile yet", async () => {
    const sessionProfile = createTemporaryTasteProfile(["C002"]);
    const onSuccess = vi.fn();

    vi.mocked(loginAccount).mockResolvedValue({
      token: "token-1",
      user: { email: "user@example.com" },
    });
    vi.mocked(fetchSavedTasteProfile).mockResolvedValue(null);
    vi.mocked(saveTasteProfile).mockResolvedValue(sessionProfile);

    render(
      <AuthDialog
        mode="login"
        onClose={vi.fn()}
        onSuccess={onSuccess}
        onSwitchMode={vi.fn()}
        profileToSave={sessionProfile}
      />,
    );

    fillLoginForm("user@example.com", "secret123");
    fireEvent.click(screen.getByRole("button", { name: "Anmelden und speichern" }));

    await waitFor(() => {
      expect(saveTasteProfile).toHaveBeenCalledTimes(1);
      expect(onSuccess).toHaveBeenCalled();
    });
    expect(
      screen.queryByRole("heading", { name: "Bestehendes Profil überschreiben?" }),
    ).toBeNull();
  });
});
