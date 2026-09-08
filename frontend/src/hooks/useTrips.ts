import {
  useMutation,
  useQuery,
  useQueryClient,
} from "@tanstack/react-query";

import { tripsApi } from "../api/trips";
import type {
  TripCreateRequest,
  TripUpdateRequest,
} from "../types/trips";

const tripKeys = {
  all: ["trips"] as const,

  list: () => [...tripKeys.all, "list"] as const,

  detail: (tripId: number) =>
    [...tripKeys.all, "detail", tripId] as const,
};

export function useTrips() {
  return useQuery({
    queryKey: tripKeys.list(),
    queryFn: tripsApi.list,
  });
}

export function useTrip(tripId: number) {
  return useQuery({
    queryKey: tripKeys.detail(tripId),
    queryFn: () => tripsApi.getById(tripId),
    enabled: Number.isFinite(tripId) && tripId > 0,
  });
}

export function useCreateTrip() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: (payload: TripCreateRequest) =>
      tripsApi.create(payload),

    onSuccess: () => {
      void queryClient.invalidateQueries({
        queryKey: tripKeys.list(),
      });
    },
  });
}

export function useUpdateTrip() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: ({
      tripId,
      payload,
    }: {
      tripId: number;
      payload: TripUpdateRequest;
    }) => tripsApi.update(tripId, payload),

    onSuccess: (trip) => {
      queryClient.setQueryData(
        tripKeys.detail(trip.id),
        trip,
      );

      void queryClient.invalidateQueries({
        queryKey: tripKeys.list(),
      });
    },
  });
}

export function useDeleteTrip() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: (tripId: number) =>
      tripsApi.remove(tripId),

    onSuccess: (_, tripId) => {
      queryClient.removeQueries({
        queryKey: tripKeys.detail(tripId),
      });

      void queryClient.invalidateQueries({
        queryKey: tripKeys.list(),
      });
    },
  });
}