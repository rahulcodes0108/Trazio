import { describe, expect, it, vi, beforeEach } from "vitest";
import { render, screen } from "@testing-library/react";
import { MemoryRouter, Route, Routes } from "react-router-dom";
import {
  QueryClient,
  QueryClientProvider,
} from "@tanstack/react-query";

import TripDetailsPage from "./TripDetailsPage";

const mockTrip = {
  id: 1,
  title: "Chennai Explorer",
  description: "A day exploring Chennai.",
  start_location: "Chennai Central",
  start_date: "2026-09-10",
  start_time: "09:00",
  available_duration_minutes: 420,
  budget_level: "moderate",
  budget_amount: 1000,
  budget_currency: "INR",
  transport_mode: "car",
  status: "draft",
  preferences: {},
  created_at: "2026-09-09T00:00:00Z",
  updated_at: "2026-09-09T00:00:00Z",
};

const mockItineraries = {
  itineraries: [],
  count: 0,
};

vi.mock("../../hooks/useTrips", () => ({
  useTrip: vi.fn(),
  useDeleteTrip: vi.fn(),
}));

vi.mock("../../hooks/useItineraries", () => ({
  useItineraries: vi.fn(),
  useGenerateItinerary: vi.fn(),
}));

import {
  useDeleteTrip,
  useTrip,
} from "../../hooks/useTrips";

import {
  useGenerateItinerary,
  useItineraries,
} from "../../hooks/useItineraries";

function createQueryClient() {
  return new QueryClient({
    defaultOptions: {
      queries: {
        retry: false,
      },
      mutations: {
        retry: false,
      },
    },
  });
}

function renderPage() {
  const queryClient = createQueryClient();

  return render(
    <QueryClientProvider client={queryClient}>
      <MemoryRouter
        initialEntries={["/trips/1"]}
      >
        <Routes>
          <Route
            path="/trips/:tripId"
            element={<TripDetailsPage />}
          />
        </Routes>
      </MemoryRouter>
    </QueryClientProvider>,
  );
}

describe("TripDetailsPage", () => {
  beforeEach(() => {
    vi.clearAllMocks();

    vi.mocked(useTrip).mockReturnValue({
      data: mockTrip,
      isLoading: false,
      isError: false,
      refetch: vi.fn(),
    } as never);

    vi.mocked(useItineraries).mockReturnValue({
      data: mockItineraries,
      isLoading: false,
      isError: false,
      error: null,
    } as never);

    vi.mocked(useGenerateItinerary).mockReturnValue({
      mutate: vi.fn(),
      mutateAsync: vi.fn(),
      isPending: false,
      isError: false,
      error: null,
    } as never);

    vi.mocked(useDeleteTrip).mockReturnValue({
      mutateAsync: vi.fn(),
      isPending: false,
    } as never);
  });

  it("renders the trip details", () => {
    renderPage();

    expect(
      screen.getByRole("heading", {
        name: "Chennai Explorer",
      }),
    ).toBeInTheDocument();

    expect(
      screen.getByText("Chennai Central"),
    ).toBeInTheDocument();

    expect(
      screen.getByText("2026-09-10"),
    ).toBeInTheDocument();

    expect(
      screen.getByText("7 hr"),
    ).toBeInTheDocument();
  });

  it("renders the loading state", () => {
    vi.mocked(useTrip).mockReturnValue({
      data: undefined,
      isLoading: true,
      isError: false,
      refetch: vi.fn(),
    } as never);

    renderPage();

    expect(
      screen.getByRole("heading", {
        name: "Loading trip...",
      }),
    ).toBeInTheDocument();
  });

  it("renders the error state", () => {
    vi.mocked(useTrip).mockReturnValue({
      data: undefined,
      isLoading: false,
      isError: true,
      refetch: vi.fn(),
    } as never);

    renderPage();

    expect(
      screen.getByRole("heading", {
        name: "Trip unavailable",
      }),
    ).toBeInTheDocument();

    expect(
      screen.getByRole("link", {
        name: "Back to trips",
      }),
    ).toBeInTheDocument();
  });

  it("provides an edit link", () => {
    renderPage();

    expect(
      screen.getByRole("link", {
        name: "Edit trip",
      }),
    ).toHaveAttribute(
      "href",
      "/trips/1/edit",
    );
  });

  it("enables itinerary generation when no itinerary exists", () => {
    renderPage();

    const button = screen.getByRole("button", {
      name: "Generate itinerary",
    });

    expect(button).toBeEnabled();
  });
});