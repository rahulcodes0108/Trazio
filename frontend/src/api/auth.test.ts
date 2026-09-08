import { beforeEach, describe, expect, it, vi } from "vitest";

import { authApi } from "./auth";
import { apiClient } from "./client";

describe("authApi", () => {
  beforeEach(() => {
    vi.restoreAllMocks();
  });

  it("registers a user", async () => {
    const response = {
      access_token: "access-token",
      refresh_token: "refresh-token",
      token_type: "bearer",
      expires_at: "2026-09-08T10:00:00Z",
    };

    vi.spyOn(apiClient, "post").mockResolvedValue({
      data: response,
    } as never);

    const result = await authApi.register({
      email: "test@example.com",
      username: "testuser",
      password: "password123",
      full_name: "Test User",
    });

    expect(result).toEqual(response);
    expect(apiClient.post).toHaveBeenCalledWith(
      "/auth/register",
      {
        email: "test@example.com",
        username: "testuser",
        password: "password123",
        full_name: "Test User",
      },
    );
  });

  it("logs in with email or username", async () => {
    const response = {
      access_token: "access-token",
      refresh_token: "refresh-token",
      token_type: "bearer",
      expires_at: "2026-09-08T10:00:00Z",
    };

    vi.spyOn(apiClient, "post").mockResolvedValue({
      data: response,
    } as never);

    const result = await authApi.login({
      email_or_username: "testuser",
      password: "password123",
    });

    expect(result).toEqual(response);
    expect(apiClient.post).toHaveBeenCalledWith(
      "/auth/login",
      {
        email_or_username: "testuser",
        password: "password123",
      },
    );
  });

  it("fetches the current user", async () => {
    const user = {
      id: 1,
      email: "test@example.com",
      username: "testuser",
      full_name: "Test User",
      is_verified: true,
      status: "active",
      created_at: "2026-09-08T10:00:00Z",
    };

    vi.spyOn(apiClient, "get").mockResolvedValue({
      data: user,
    } as never);

    const result = await authApi.me();

    expect(result).toEqual(user);
    expect(apiClient.get).toHaveBeenCalledWith("/auth/me");
  });
});