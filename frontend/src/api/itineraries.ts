import apiClient from "./client";
import type {
  Itinerary,
  ItineraryListResponse,
  ItineraryStopListResponse,
  ReplanRequest,
} from "../types/itineraries";

export async function listItineraries(
  tripId: number,
): Promise<ItineraryListResponse> {
  const response = await apiClient.get<ItineraryListResponse>(
    `/itineraries/trips/${tripId}`,
  );

  return response.data;
}

export async function generateItinerary(
  tripId: number,
): Promise<Itinerary> {
  const response = await apiClient.post<Itinerary>(
    `/itineraries/trips/${tripId}/generate`,
  );

  return response.data;
}

export async function getItinerary(
  itineraryId: number,
): Promise<Itinerary> {
  const response = await apiClient.get<Itinerary>(
    `/itineraries/${itineraryId}`,
  );

  return response.data;
}

export async function getItineraryStops(
  itineraryId: number,
): Promise<ItineraryStopListResponse> {
  const response = await apiClient.get<ItineraryStopListResponse>(
    `/itineraries/${itineraryId}/stops`,
  );

  return response.data;
}

export async function replanItinerary(
  itineraryId: number,
  request: ReplanRequest,
): Promise<Itinerary> {
  const response = await apiClient.post<Itinerary>(
    `/itineraries/${itineraryId}/replan`,
    request,
  );

  return response.data;
}