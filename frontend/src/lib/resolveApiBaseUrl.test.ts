import { afterEach, describe, expect, it, vi } from "vitest";

import { resolveApiBaseUrl } from "./apiClient";

describe("resolveApiBaseUrl", () => {
  afterEach(() => {
    vi.unstubAllEnvs();
  });

  it("uses VITE_API_BASE_URL when set", () => {
    vi.stubEnv("VITE_API_BASE_URL", "https://api.example.test/");
    expect(resolveApiBaseUrl()).toBe("https://api.example.test");
  });

  it("falls back to the local dev default", () => {
    vi.stubEnv("VITE_API_BASE_URL", "");
    expect(resolveApiBaseUrl()).toBe("http://127.0.0.1:8000");
  });
});
