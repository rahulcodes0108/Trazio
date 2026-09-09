import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import {
  MemoryRouter,
  Route,
  Routes,
} from "react-router-dom";
import { beforeEach, describe, expect, it, vi } from "vitest";

import ItineraryPage from "./ItineraryPage";

import {
  useItinerary,
  useItineraryStops,
  useReplanItinerary,
} from "../../hooks/useItineraries";
import { useDestinations } from "../../hooks/useDestinations";

import type {
  Itinerary,
  ItineraryStop,
} from "../../types/itineraries";
import type { Destination } from "../../types/destinations";

vi.mock("../../hooks/useItineraries", () => ({
  useItinerary: vi.fn(),
  useItineraryStops: vi.fn(),
  useReplanItinerary: vi.fn(),
}));

vi.mock("../../hooks/useDestinations", () => ({
  useDestinations: vi.fn(),
}));

vi.mock("../../components/maps/ItineraryMap", () => ({
  default: ({
    stops,
    selectedStopId,
    onStopSelect,
  }: {
    stops: Array<{
      id: number;
      sequence: number;
      name: string;
      coordinates: [number, number];
    }>;
    selectedStopId: number | null;
    onStopSelect: (stopId: number) => void;
  }) => (
    <div data-testid="itinerary-map">
      <span>
        Selected: {selectedStopId ?? "none"}
      </span>

      {stops.map((stop) => (
        <button
          key={stop.id}
          type="button"
          onClick={() => onStopSelect(stop.id)}
        >
          Map stop {stop.sequence}
        </button>
      ))}
    </div>
  ),
}));

const mockedUseItinerary = vi.mocked(useItinerary);
const mockedUseItineraryStops = vi.mocked(useItineraryStops);
const mockedUseReplanItinerary = vi.mocked(useReplanItinerary);
const mockedUseDestinations = vi.mocked(useDestinations);

const itinerary: Itinerary = {
  id: 10,
  trip_id: 1,
  version: 1,
  status: "optimized",
  notes: "Optimized for time and preferences.",
  total_duration_minutes: 420,
  estimated_travel_duration_minutes: 90,
  estimated_cost: 850,
  estimated_cost_currency: "INR",
  is_optimized: true,
  stop_count: 2,
  created_at: "2026-09-09T10:00:00Z",
  updated_at: "2026-09-09T10:00:00Z",
};

const stops: ItineraryStop[] = [
  {
    id: 101,
    itinerary_id: 10,
    destination_id: 1,
    sequence: 1,
    planned_arrival: "2026-09-09T14:30:00",
    planned_departure: "2026-09-09T16:00:00",
    visit_duration_minutes: 90,
    estimated_travel_duration_minutes: 0,
    estimated_travel_distance_km: 0,
    travel_mode: "car",
    selection_reason: "Strong preference match.",
    notes: null,
    estimated_cost: 100,
    estimated_cost_currency: "INR",
    created_at: "2026-09-09T10:00:00Z",
    updated_at: "2026-09-09T10:00:00Z",
  },
  {
    id: 102,
    itinerary_id: 10,
    destination_id: 2,
    sequence: 2,
    planned_arrival: "2026-09-09T16:30:00",
    planned_departure: "2026-09-09T18:00:00",
    visit_duration_minutes: 90,
    estimated_travel_duration_minutes: 30,
    estimated_travel_distance_km: 8.5,
    travel_mode: "car",
    selection_reason: "Good experience and route fit.",
    notes: "Carry water.",
    estimated_cost: 150,
    estimated_cost_currency: "INR",
    created_at: "2026-09-09T10:00:00Z",
    updated_at: "2026-09-09T10:00:00Z",
  },
];

const destinations: Destination[] = [
  {
    id: 1,
    name: "Marina Beach",
    slug: "marina-beach",
    description: "A famous Chennai beach.",
    image_url: null,
    category: "beach",
    location: "POINT(80.2824 13.0499)",

    address_line1: null,
    address_line2: null,
    city: "Chennai",
    state_province: "Tamil Nadu",
    postal_code: null,
    country: "India",

    opening_hours: null,
    entry_fee: null,
    entry_fee_currency: null,

    average_visit_duration_minutes: 90,

    accessibility: "unknown",
    accessibility_notes: null,

    popularity_score: 90,
    is_active: true,

    website_url: null,
    phone_number: null,
    email: null,

    created_at: "2026-09-09T10:00:00Z",
    updated_at: "2026-09-09T10:00:00Z",
  },
  {
    id: 2,
    name: "Kapaleeshwarar Temple",
    slug: "kapaleeshwarar-temple",
    description: "A historic Chennai temple.",
    image_url: null,
    category: "heritage",
    location: "POINT(80.2684 13.0338)",

    address_line1: null,
    address_line2: null,
    city: "Chennai",
    state_province: "Tamil Nadu",
    postal_code: null,
    country: "India",

    opening_hours: null,
    entry_fee: null,
    entry_fee_currency: null,

    average_visit_duration_minutes: 90,

    accessibility: "unknown",
    accessibility_notes: null,

    popularity_score: 85,
    is_active: true,

    website_url: null,
    phone_number: null,
    email: null,

    created_at: "2026-09-09T10:00:00Z",
    updated_at: "2026-09-09T10:00:00Z",
  },
];

function renderPage() {
  return render(
    <MemoryRouter initialEntries={["/itineraries/10"]}>
      <Routes>
        <Route
          path="/itineraries/:itineraryId"
          element={<ItineraryPage />}
        />
      </Routes>
    </MemoryRouter>,
  );
}

describe("ItineraryPage", () => {
  beforeEach(() => {
    vi.clearAllMocks();

    mockedUseItinerary.mockReturnValue({
      data: itinerary,
      isLoading: false,
      isError: false,
      error: null,
    } as ReturnType<typeof useItinerary>);

    mockedUseItineraryStops.mockReturnValue({
      data: {
        stops,
      },
      isLoading: false,
      isError: false,
      error: null,
    } as ReturnType<typeof useItineraryStops>);

    mockedUseDestinations.mockReturnValue({
      data: {
        destinations,
      },
      isLoading: false,
      isError: false,
      error: null,
    } as ReturnType<typeof useDestinations>);

    mockedUseReplanItinerary.mockReturnValue({
      mutateAsync: vi.fn(),
      isPending: false,
      isError: false,
      error: null,
      reset: vi.fn(),
    } as unknown as ReturnType<typeof useReplanItinerary>);
  });

  it("renders the itinerary details", () => {
    renderPage();

    expect(
      screen.getByRole("heading", {
        name: /itinerary · version 1/i,
      }),
    ).toBeInTheDocument();

    expect(
      screen.getByText("optimized"),
    ).toBeInTheDocument();

    expect(
      screen.getByText("7 hr"),
    ).toBeInTheDocument();

    expect(
      screen.getByText("INR 850"),
    ).toBeInTheDocument();

    expect(
      screen.getByText("Marina Beach"),
    ).toBeInTheDocument();

    expect(
      screen.getByText("Kapaleeshwarar Temple"),
    ).toBeInTheDocument();
  });

  it("renders the loading state", () => {
    mockedUseItinerary.mockReturnValue({
      data: undefined,
      isLoading: true,
      isError: false,
      error: null,
    } as ReturnType<typeof useItinerary>);

    renderPage();

    expect(
      screen.getByText(/loading itinerary/i),
    ).toBeInTheDocument();
  });

  it("renders the itinerary error state", () => {
    mockedUseItinerary.mockReturnValue({
      data: undefined,
      isLoading: false,
      isError: true,
      error: new Error("Failed to load itinerary"),
    } as ReturnType<typeof useItinerary>);

    renderPage();

    expect(
      screen.getByText(/failed to load itinerary/i),
    ).toBeInTheDocument();
  });

  it("renders the itinerary map", () => {
    renderPage();

    expect(
      screen.getByTestId("itinerary-map"),
    ).toBeInTheDocument();

    expect(
      screen.getByRole("button", {
        name: "Map stop 1",
      }),
    ).toBeInTheDocument();

    expect(
      screen.getByRole("button", {
        name: "Map stop 2",
      }),
    ).toBeInTheDocument();
  });

  it("updates selected stop when a map stop is selected", () => {
    renderPage();

    expect(
      screen.getByText("Selected: none"),
    ).toBeInTheDocument();

    fireEvent.click(
      screen.getByRole("button", {
        name: "Map stop 1",
      }),
    );

    expect(
      screen.getByText("Selected: 101"),
    ).toBeInTheDocument();
  });

  it("opens the dynamic replanning panel", () => {
    renderPage();

    fireEvent.click(
      screen.getByRole("button", {
        name: /replan trip/i,
      }),
    );

    expect(
      screen.getByText("DYNAMIC PLANNING"),
    ).toBeInTheDocument();

    expect(
      screen.getByText(
        "Which destinations are unavailable?",
      ),
    ).toBeInTheDocument();

    expect(
      screen.getAllByText("Marina Beach").length,
    ).toBeGreaterThan(1);

    expect(
      screen.getAllByText("Kapaleeshwarar Temple").length,
    ).toBeGreaterThan(1);

    expect(
      screen.getByRole("textbox", {
        name: /reason/i,
      }),
    ).toBeInTheDocument();

    expect(
      screen.getByRole("button", {
        name: /create new itinerary/i,
      }),
    ).toBeDisabled();
  });

  it("keeps the replan button disabled until a destination is selected", () => {
    renderPage();

    fireEvent.click(
      screen.getByRole("button", {
        name: /replan trip/i,
      }),
    );

    const createButton = screen.getByRole("button", {
      name: /create new itinerary/i,
    });

    expect(createButton).toBeDisabled();

    const checkboxes = screen.getAllByRole("checkbox");

    expect(checkboxes).toHaveLength(2);

    fireEvent.click(checkboxes[0]);

    expect(createButton).not.toBeDisabled();
  });

  it("submits unavailable destination IDs and reason", async () => {
    const mutateAsync = vi.fn().mockResolvedValue({
      ...itinerary,
      id: 11,
      version: 2,
    });

    mockedUseReplanItinerary.mockReturnValue({
      mutateAsync,
      isPending: false,
      isError: false,
      error: null,
      reset: vi.fn(),
    } as unknown as ReturnType<typeof useReplanItinerary>);

    renderPage();

    fireEvent.click(
      screen.getByRole("button", {
        name: /replan trip/i,
      }),
    );

    const checkboxes = screen.getAllByRole("checkbox");

    expect(checkboxes).toHaveLength(2);

    fireEvent.click(checkboxes[0]);

    const reasonInput = screen.getByRole("textbox", {
      name: /reason/i,
    });

    fireEvent.change(reasonInput, {
      target: {
        value: "Destination closed unexpectedly",
      },
    });

    fireEvent.click(
      screen.getByRole("button", {
        name: /create new itinerary/i,
      }),
    );

    await waitFor(() => {
      expect(mutateAsync).toHaveBeenCalledWith({
        unavailable_destination_ids: [1],
        reason: "Destination closed unexpectedly",
      });
    });
  });

  it("allows cancelling the replan panel", () => {
    renderPage();

    fireEvent.click(
      screen.getByRole("button", {
        name: /replan trip/i,
      }),
    );

    expect(
      screen.getByText(
        "Which destinations are unavailable?",
      ),
    ).toBeInTheDocument();

    fireEvent.click(
      screen.getByRole("button", {
        name: "Cancel",
      }),
    );

    expect(
      screen.queryByText(
        "Which destinations are unavailable?",
      ),
    ).not.toBeInTheDocument();
  });

  it("renders the stops error state", () => {
    mockedUseItineraryStops.mockReturnValue({
      data: undefined,
      isLoading: false,
      isError: true,
      error: new Error("Failed to load stops"),
    } as ReturnType<typeof useItineraryStops>);

    renderPage();

    expect(
      screen.getByText("Failed to load stops"),
    ).toBeInTheDocument();

    expect(
      screen.getByText("Stops unavailable"),
    ).toBeInTheDocument();
  });
});