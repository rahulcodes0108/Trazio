import { describe, expect, it, vi, beforeEach } from "vitest";

import {
  generateItinerary,
  getItinerary,
  getItineraryStops,
  listItineraries,
  replanItinerary,
} from "./itineraries";

import apiClient from "./client";

vi.mock("./client", () => ({
  default: {
    get: vi.fn(),
    post: vi.fn(),
  },
}));

describe("itinerary API", () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it("lists itineraries for a trip", async () => {
    const responseData = {
      itineraries: [
        {
          id: 1,
          trip_id: 10,
          version: 1,
          status: "draft",
          notes: null,
          total_duration_minutes: 420,
          estimated_travel_duration_minutes: 60,
          estimated_cost: 500,
          estimated_cost_currency: "INR",
          is_optimized: true,
          stop_count: 4,
          created_at: "2026-09-09T10:00:00Z",
          updated_at: "2026-09-09T10:00:00Z",
        },
      ],
      count: 1,
    };

    vi.mocked(apiClient.get).mockResolvedValueOnce({
      data: responseData,
    });

    const result = await listItineraries(10);

    expect(apiClient.get).toHaveBeenCalledWith(
      "/itineraries/trips/10",
    );
    expect(result).toEqual(responseData);
  });

  it("generates an itinerary for a trip", async () => {
    const responseData = {
      id: 2,
      trip_id: 10,
      version: 2,
      status: "draft",
      notes: "Generated itinerary",
      total_duration_minutes: 420,
      estimated_travel_duration_minutes: 75,
      estimated_cost: 600,
      estimated_cost_currency: "INR",
      is_optimized: true,
      stop_count: 5,
      created_at: "2026-09-09T10:00:00Z",
      updated_at: "2026-09-09T10:00:00Z",
    };

    vi.mocked(apiClient.post).mockResolvedValueOnce({
      data: responseData,
    });

    const result = await generateItinerary(10);

    expect(apiClient.post).toHaveBeenCalledWith(
      "/itineraries/trips/10/generate",
    );
    expect(result).toEqual(responseData);
  });

  it("gets an itinerary by ID", async () => {
    const responseData = {
      id: 2,
      trip_id: 10,
      version: 2,
      status: "draft",
      notes: null,
      total_duration_minutes: 420,
      estimated_travel_duration_minutes: 75,
      estimated_cost: 600,
      estimated_cost_currency: "INR",
      is_optimized: true,
      stop_count: 5,
      created_at: "2026-09-09T10:00:00Z",
      updated_at: "2026-09-09T10:00:00Z",
    };

    vi.mocked(apiClient.get).mockResolvedValueOnce({
      data: responseData,
    });

    const result = await getItinerary(2);

    expect(apiClient.get).toHaveBeenCalledWith(
      "/itineraries/2",
    );
    expect(result).toEqual(responseData);
  });

  it("gets stops for an itinerary", async () => {
    const responseData = {
      stops: [
        {
          id: 1,
          itinerary_id: 2,
          destination_id: 12,
          sequence: 1,
          planned_arrival: "2026-09-09T09:00:00Z",
          planned_departure: "2026-09-09T10:00:00Z",
          visit_duration_minutes: 60,
          estimated_travel_duration_minutes: 20,
          estimated_travel_distance_km: 5.2,
          travel_mode: "driving",
          selection_reason: "Strong preference match and low travel time.",
          notes: null,
          estimated_cost: 100,
          estimated_cost_currency: "INR",
          created_at: "2026-09-09T10:00:00Z",
          updated_at: "2026-09-09T10:00:00Z",
        },
      ],
      count: 1,
    };

    vi.mocked(apiClient.get).mockResolvedValueOnce({
      data: responseData,
    });

    const result = await getItineraryStops(2);

    expect(apiClient.get).toHaveBeenCalledWith(
      "/itineraries/2/stops",
    );
    expect(result).toEqual(responseData);
  });

  it("replans an itinerary", async () => {
    const request = {
      unavailable_destination_ids: [12, 15],
      reason: "Destination became unavailable.",
    };

    const responseData = {
      id: 3,
      trip_id: 10,
      version: 3,
      status: "draft",
      notes: "Replanned itinerary",
      total_duration_minutes: 420,
      estimated_travel_duration_minutes: 80,
      estimated_cost: 650,
      estimated_cost_currency: "INR",
      is_optimized: true,
      stop_count: 5,
      created_at: "2026-09-09T11:00:00Z",
      updated_at: "2026-09-09T11:00:00Z",
    };

    vi.mocked(apiClient.post).mockResolvedValueOnce({
      data: responseData,
    });

    const result = await replanItinerary(2, request);

    expect(apiClient.post).toHaveBeenCalledWith(
      "/itineraries/2/replan",
      request,
    );
    expect(result).toEqual(responseData);
  });
});