import { describe, expect, it } from "vitest";

import { pathForRoute, routeFromPath } from "./routes";

describe("routeFromPath", () => {
  it("maps known routes", () => {
    expect(routeFromPath("/aktuell")).toBe("aktuell");
    expect(routeFromPath("/neuheiten")).toBe("aktuell");
    expect(routeFromPath("/entdecken")).toBe("entdecken");
    expect(routeFromPath("/playlists")).toBe("playlists");
  });

  it("maps the setup path to the music profile shell", () => {
    expect(routeFromPath("/profil/setup")).toBe("musikprofil");
  });

  it("falls back to the welcome screen", () => {
    expect(routeFromPath("/")).toBe("willkommen");
    expect(routeFromPath("/unbekannt")).toBe("willkommen");
  });
});

describe("pathForRoute", () => {
  it("maps the neuheiten page to /neuheiten", () => {
    expect(pathForRoute("aktuell")).toBe("/neuheiten");
    expect(pathForRoute("willkommen")).toBe("/");
    expect(pathForRoute("entdecken")).toBe("/entdecken");
  });
});
