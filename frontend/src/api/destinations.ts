import apiClient from "./client";
import type {
  Destination,
  DestinationListResponse,
} from "../types/destinations";

export interface ListDestinationsParams {
  skip?: number;
  limit?: number;
}

export const destinationsApi = {
  async list(
    params?: ListDestinationsParams,
  ): Promise<DestinationListResponse> {
    const { data } = await apiClient.get<DestinationListResponse>(
      "/destinations",
      {
        params,
      },
    );

    return data;
  },

  async getById(destinationId: number): Promise<Destination> {
    const { data } = await apiClient.get<Destination>(
      `/destinations/${destinationId}`,
    );

    return data;
  },

  async getBySlug(slug: string): Promise<Destination> {
    const { data } = await apiClient.get<Destination>(
      `/destinations/slug/${encodeURIComponent(slug)}`,
    );

    return data;
  },
};