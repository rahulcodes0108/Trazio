import { beforeEach, describe, expect, it, vi } from "vitest";
import apiClient from "./client";
import { destinationsApi } from "./destinations";

vi.mock("./client", () => ({
  default: {
    get: vi.fn(),
  },
}));

const mockedGet = vi.mocked(apiClient.get);

describe("destinationsApi", () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it("lists destinations", async () => {
    const response = {
      destinations: [],
      count: 0,
    };

    mockedGet.mockResolvedValueOnce({
      data: response,
    } as never);

    const result = await destinationsApi.list();

    expect(mockedGet).toHaveBeenCalledWith("/destinations", {
      params: undefined,
    });

    expect(result).toEqual(response);
  });

  it("lists destinations with pagination", async () => {
    const response = {
      destinations: [],
      count: 0,
    };

    mockedGet.mockResolvedValueOnce({
      data: response,
    } as never);

    await destinationsApi.list({
      skip: 10,
      limit: 20,
    });

    expect(mockedGet).toHaveBeenCalledWith("/destinations", {
      params: {
        skip: 10,
        limit: 20,
      },
    });
  });

  it("gets a destination by ID", async () => {
    const destination = {
      id: 1,
      name: "Marina Beach",
    };

    mockedGet.mockResolvedValueOnce({
      data: destination,
    } as never);

    const result = await destinationsApi.getById(1);

    expect(mockedGet).toHaveBeenCalledWith("/destinations/1");
    expect(result).toEqual(destination);
  });

  it("gets a destination by slug", async () => {
    const destination = {
      id: 1,
      name: "Marina Beach",
      slug: "marina-beach",
    };

    mockedGet.mockResolvedValueOnce({
      data: destination,
    } as never);

    const result = await destinationsApi.getBySlug("marina-beach");

    expect(mockedGet).toHaveBeenCalledWith(
      "/destinations/slug/marina-beach",
    );

    expect(result).toEqual(destination);
  });

  it("encodes destination slugs", async () => {
    mockedGet.mockResolvedValueOnce({
      data: {},
    } as never);

    await destinationsApi.getBySlug("marina beach");

    expect(mockedGet).toHaveBeenCalledWith(
      "/destinations/slug/marina%20beach",
    );
  });
});