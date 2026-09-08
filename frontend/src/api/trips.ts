import apiClient from "./client";

import type {
  Trip,
  TripCreateRequest,
  TripListResponse,
  TripUpdateRequest,
} from "../types/trips";

export const tripsApi = {
  async list(): Promise<TripListResponse> {
    const { data } = await apiClient.get<TripListResponse>("/trips");

    return data;
  },

  async getById(tripId: number): Promise<Trip> {
    const { data } = await apiClient.get<Trip>(
      `/trips/${tripId}`,
    );

    return data;
  },

  async create(payload: TripCreateRequest): Promise<Trip> {
    const { data } = await apiClient.post<Trip>(
      "/trips",
      payload,
    );

    return data;
  },

  async update(
    tripId: number,
    payload: TripUpdateRequest,
  ): Promise<Trip> {
    const { data } = await apiClient.patch<Trip>(
      `/trips/${tripId}`,
      payload,
    );

    return data;
  },

  async remove(tripId: number): Promise<void> {
    await apiClient.delete(`/trips/${tripId}`);
  },
};