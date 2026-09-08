import { beforeEach, describe, expect, it, vi } from "vitest";

import { apiClient } from "./client";
import { tripsApi } from "./trips";

describe("tripsApi", () => {
  beforeEach(() => {
    vi.restoreAllMocks();
  });

  it("lists trips", async () => {
    const response = {
      trips: [],
      count: 0,
    };

    vi.spyOn(apiClient, "get").mockResolvedValue({
      data: response,
    } as never);

    const result = await tripsApi.list();

    expect(result).toEqual(response);
    expect(apiClient.get).toHaveBeenCalledWith("/trips");
  });

  it("gets a trip by id", async () => {
    const trip = {
      id: 12,
      title: "Chennai Day Trip",
    };

    vi.spyOn(apiClient, "get").mockResolvedValue({
      data: trip,
    } as never);

    const result = await tripsApi.getById(12);

    expect(result).toEqual(trip);
    expect(apiClient.get).toHaveBeenCalledWith("/trips/12");
  });

  it("creates a trip", async () => {
    const payload = {
      title: "Chennai Day Trip",
      start_location: "Chennai",
      start_date: "2026-09-10",
      start_time: "09:00",
    };

    const trip = {
      id: 12,
      ...payload,
    };

    vi.spyOn(apiClient, "post").mockResolvedValue({
      data: trip,
    } as never);

    const result = await tripsApi.create(payload);

    expect(result).toEqual(trip);
    expect(apiClient.post).toHaveBeenCalledWith(
      "/trips",
      payload,
    );
  });

  it("updates a trip", async () => {
    const payload = {
      title: "Updated Chennai Trip",
    };

    const trip = {
      id: 12,
      title: "Updated Chennai Trip",
    };

    vi.spyOn(apiClient, "patch").mockResolvedValue({
      data: trip,
    } as never);

    const result = await tripsApi.update(12, payload);

    expect(result).toEqual(trip);
    expect(apiClient.patch).toHaveBeenCalledWith(
      "/trips/12",
      payload,
    );
  });

  it("deletes a trip", async () => {
    const deleteSpy = vi
      .spyOn(apiClient, "delete")
      .mockResolvedValue({} as never);

    await tripsApi.remove(12);

    expect(deleteSpy).toHaveBeenCalledWith("/trips/12");
  });
});