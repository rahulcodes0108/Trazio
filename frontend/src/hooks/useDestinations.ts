import {
  useQuery,
} from "@tanstack/react-query";

import { destinationsApi } from "../api/destinations";

const destinationKeys = {
  all: ["destinations"] as const,

  list: (skip = 0, limit = 100) =>
    [...destinationKeys.all, "list", skip, limit] as const,

  detail: (destinationId: number) =>
    [...destinationKeys.all, "detail", destinationId] as const,

  slug: (slug: string) =>
    [...destinationKeys.all, "slug", slug] as const,
};

export function useDestinations(
  skip = 0,
  limit = 100,
) {
  return useQuery({
    queryKey: destinationKeys.list(skip, limit),
    queryFn: () =>
      destinationsApi.list({
        skip,
        limit,
      }),
  });
}

export function useDestination(destinationId: number) {
  return useQuery({
    queryKey: destinationKeys.detail(destinationId),
    queryFn: () => destinationsApi.getById(destinationId),
    enabled:
      Number.isFinite(destinationId) &&
      destinationId > 0,
  });
}

export function useDestinationBySlug(slug: string) {
  return useQuery({
    queryKey: destinationKeys.slug(slug),
    queryFn: () => destinationsApi.getBySlug(slug),
    enabled: Boolean(slug),
  });
}