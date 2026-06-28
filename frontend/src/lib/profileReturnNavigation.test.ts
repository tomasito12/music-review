import { describe, expect, it } from "vitest";

import {
  captureProfileReturnRoute,
  resolveProfileFinishRoute,
  startInitialProfileSetup,
  startProfileEdit,
} from "./profileReturnNavigation";

describe("captureProfileReturnRoute", () => {
  it("stores content routes as return targets", () => {
    expect(captureProfileReturnRoute("aktuell")).toBe("aktuell");
    expect(captureProfileReturnRoute("entdecken")).toBe("entdecken");
    expect(captureProfileReturnRoute("playlists")).toBe("playlists");
  });

  it("keeps the previous return route for non-content pages", () => {
    expect(captureProfileReturnRoute("musikprofil", "aktuell")).toBe("aktuell");
    expect(captureProfileReturnRoute("konto", "playlists")).toBe("playlists");
    expect(captureProfileReturnRoute("willkommen", "entdecken")).toBe("entdecken");
  });

  it("returns null when there is no valid return route", () => {
    expect(captureProfileReturnRoute("musikprofil")).toBeNull();
    expect(captureProfileReturnRoute("willkommen")).toBeNull();
  });
});

describe("startInitialProfileSetup", () => {
  it("marks the flow as initial setup without a return route", () => {
    expect(startInitialProfileSetup()).toEqual({
      mode: "initial",
      returnRoute: null,
    });
  });
});

describe("startProfileEdit", () => {
  it("captures the originating content route", () => {
    expect(startProfileEdit("aktuell")).toEqual({
      mode: "edit",
      returnRoute: "aktuell",
    });
  });

  it("preserves an existing return route when reopening from musikprofil", () => {
    expect(startProfileEdit("musikprofil", "playlists")).toEqual({
      mode: "edit",
      returnRoute: "playlists",
    });
  });
});

describe("resolveProfileFinishRoute", () => {
  it("always sends first-time setup to entdecken", () => {
    expect(
      resolveProfileFinishRoute({
        mode: "initial",
        returnRoute: null,
        isAuthenticated: false,
      }),
    ).toBe("entdecken");
    expect(
      resolveProfileFinishRoute({
        mode: "initial",
        returnRoute: "aktuell",
        isAuthenticated: true,
      }),
    ).toBe("entdecken");
  });

  it("returns to the captured route after editing", () => {
    expect(
      resolveProfileFinishRoute({
        mode: "edit",
        returnRoute: "aktuell",
        isAuthenticated: true,
      }),
    ).toBe("aktuell");
    expect(
      resolveProfileFinishRoute({
        mode: "edit",
        returnRoute: "playlists",
        isAuthenticated: false,
      }),
    ).toBe("playlists");
  });

  it("falls back based on authentication when no return route exists", () => {
    expect(
      resolveProfileFinishRoute({
        mode: "edit",
        returnRoute: null,
        isAuthenticated: true,
      }),
    ).toBe("aktuell");
    expect(
      resolveProfileFinishRoute({
        mode: "edit",
        returnRoute: null,
        isAuthenticated: false,
      }),
    ).toBe("entdecken");
  });
});
