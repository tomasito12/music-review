import { describe, expect, it, vi } from "vitest";

import { createApiClient } from "./apiClient";

describe("createApiClient", () => {
  it("passes the bearer token to authenticated requests", async () => {
    const fetchMock = vi.fn().mockResolvedValue(
      new Response(JSON.stringify({ profile: { genres: [] } }), { status: 200 }),
    );
    vi.stubGlobal("fetch", fetchMock);

    const client = createApiClient("session-token");
    await client.get("/v1/me/taste-profile");

    const requestInit = fetchMock.mock.calls[0]?.[1] as RequestInit;
    const headers = new Headers(requestInit.headers);
    expect(headers.get("Authorization")).toBe("Bearer session-token");

    vi.unstubAllGlobals();
  });

  it("omits authorization when no token is available", async () => {
    const fetchMock = vi.fn().mockResolvedValue(
      new Response(JSON.stringify({ items: [] }), { status: 200 }),
    );
    vi.stubGlobal("fetch", fetchMock);

    const client = createApiClient(null);
    await client.get("/v1/presets");

    const requestInit = fetchMock.mock.calls[0]?.[1] as RequestInit;
    const headers = new Headers(requestInit.headers);
    expect(headers.get("Authorization")).toBeNull();

    vi.unstubAllGlobals();
  });
});
