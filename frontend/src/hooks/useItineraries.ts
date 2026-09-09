import {
  useMutation,
  useQuery,
  useQueryClient,
} from "@tanstack/react-query";

import {
  generateItinerary,
  getItinerary,
  getItineraryStops,
  listItineraries,
  replanItinerary,
} from "../api/itineraries";

export const itineraryKeys = {
  all: ["itineraries"] as const,

  byTrip: (tripId: number) =>
    [...itineraryKeys.all, "trip", tripId] as const,

  detail: (itineraryId: number) =>
    [...itineraryKeys.all, "detail", itineraryId] as const,

  stops: (itineraryId: number) =>
    [...itineraryKeys.all, "stops", itineraryId] as const,
};

export function useItineraries(tripId: number) {
  return useQuery({
    queryKey: itineraryKeys.byTrip(tripId),
    queryFn: () => listItineraries(tripId),
    enabled: Number.isFinite(tripId) && tripId > 0,
  });
}

export function useItinerary(itineraryId: number) {
  return useQuery({
    queryKey: itineraryKeys.detail(itineraryId),
    queryFn: () => getItinerary(itineraryId),
    enabled: Number.isFinite(itineraryId) && itineraryId > 0,
  });
}

export function useItineraryStops(itineraryId: number) {
  return useQuery({
    queryKey: itineraryKeys.stops(itineraryId),
    queryFn: () => getItineraryStops(itineraryId),
    enabled: Number.isFinite(itineraryId) && itineraryId > 0,
  });
}

export function useGenerateItinerary(tripId: number) {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: () => generateItinerary(tripId),

    onSuccess: (itinerary) => {
      void queryClient.invalidateQueries({
        queryKey: itineraryKeys.byTrip(tripId),
      });

      queryClient.setQueryData(
        itineraryKeys.detail(itinerary.id),
        itinerary,
      );
    },
  });
}

export function useReplanItinerary(itineraryId: number) {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: (request: Parameters<typeof replanItinerary>[1]) =>
      replanItinerary(itineraryId, request),

    onSuccess: (itinerary) => {
      void queryClient.invalidateQueries({
        queryKey: itineraryKeys.byTrip(itinerary.trip_id),
      });

      queryClient.setQueryData(
        itineraryKeys.detail(itinerary.id),
        itinerary,
      );
    },
  });
}