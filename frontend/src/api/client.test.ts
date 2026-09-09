import { beforeEach, describe, expect, it, vi } from "vitest";

import { apiClient } from "./client";
import { tokenStorage } from "../lib/tokenStorage";

describe("apiClient", () => {
  beforeEach(() => {
    tokenStorage.clear();
    vi.restoreAllMocks();
  });

  it("uses the configured API base URL", () => {
    expect(apiClient.defaults.baseURL).toBe(
      "http://localhost:8000",
    );
  });

  it("stores and retrieves authentication tokens", () => {
    tokenStorage.setTokens("access-token", "refresh-token");

    expect(tokenStorage.getAccessToken()).toBe("access-token");
    expect(tokenStorage.getRefreshToken()).toBe("refresh-token");
  });

  it("clears authentication tokens", () => {
    tokenStorage.setTokens("access-token", "refresh-token");

    tokenStorage.clear();

    expect(tokenStorage.getAccessToken()).toBeNull();
    expect(tokenStorage.getRefreshToken()).toBeNull();
  });
});