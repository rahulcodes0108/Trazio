import {
  render,
  screen,
} from "@testing-library/react";
import {
  MemoryRouter,
  Route,
  Routes,
} from "react-router-dom";
import {
  beforeEach,
  describe,
  expect,
  it,
  vi,
} from "vitest";

import ActiveTripPage from "./ActiveTripPage";

import {
  useItinerary,
  useItineraryStops,
} from "../../hooks/useItineraries";

import { useDestinations } from "../../hooks/useDestinations";

import {
  useLocationTracker,
} from "../../hooks/useLocationTracker";

vi.mock(
  "../../hooks/useItineraries",
  () => ({
    useItinerary: vi.fn(),
    useItineraryStops: vi.fn(),
  }),
);

vi.mock(
  "../../hooks/useDestinations",
  () => ({
    useDestinations: vi.fn(),
  }),
);

vi.mock(
  "../../hooks/useLocationTracker",
  () => ({
    useLocationTracker: vi.fn(),
  }),
);

const mockedUseItinerary =
  vi.mocked(useItinerary);

const mockedUseItineraryStops =
  vi.mocked(useItineraryStops);

const mockedUseDestinations =
  vi.mocked(useDestinations);

const mockedUseLocationTracker =
  vi.mocked(useLocationTracker);

const itinerary = {
  id: 10,
  trip_id: 1,
  version: 1,
  status: "optimized" as const,
  notes: null,
  total_duration_minutes: 420,
  estimated_travel_duration_minutes: 90,
  estimated_cost: 850,
  estimated_cost_currency: "INR",
  is_optimized: true,
  stop_count: 2,
  created_at:
    "2026-09-10T06:00:00Z",
  updated_at:
    "2026-09-10T06:00:00Z",
};

const stops = [
  {
    id: 101,
    itinerary_id: 10,
    destination_id: 1,
    sequence: 1,
    planned_arrival:
      "2026-09-10T09:00:00Z",
    planned_departure:
      "2026-09-10T10:30:00Z",
    visit_duration_minutes: 90,
    estimated_travel_duration_minutes: 0,
    estimated_travel_distance_km: 0,
    travel_mode: "driving",
    selection_reason:
      "High preference match",
    notes: null,
    estimated_cost: 0,
    estimated_cost_currency: "INR",
    created_at:
      "2026-09-10T06:00:00Z",
    updated_at:
      "2026-09-10T06:00:00Z",
  },
  {
    id: 102,
    itinerary_id: 10,
    destination_id: 2,
    sequence: 2,
    planned_arrival:
      "2026-09-10T11:00:00Z",
    planned_departure:
      "2026-09-10T12:30:00Z",
    visit_duration_minutes: 90,
    estimated_travel_duration_minutes: 30,
    estimated_travel_distance_km: 5,
    travel_mode: "driving",
    selection_reason:
      "Strong heritage match",
    notes: null,
    estimated_cost: 50,
    estimated_cost_currency: "INR",
    created_at:
      "2026-09-10T06:00:00Z",
    updated_at:
      "2026-09-10T06:00:00Z",
  },
];

const destinations = [
  {
    id: 1,
    name: "Marina Beach",
    slug: "marina-beach",
    description:
      "A famous Chennai beach.",
    image_url: null,
    category: "beach",
    location:
      "POINT(80.2824 13.0499)",
    address_line1: null,
    address_line2: null,
    city: "Chennai",
    state_province:
      "Tamil Nadu",
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
    created_at:
      "2026-09-10T06:00:00Z",
    updated_at:
      "2026-09-10T06:00:00Z",
  },
  {
    id: 2,
    name: "Kapaleeshwarar Temple",
    slug: "kapaleeshwarar-temple",
    description:
      "A historic Chennai temple.",
    image_url: null,
    category: "heritage",
    location:
      "POINT(80.2684 13.0338)",
    address_line1: null,
    address_line2: null,
    city: "Chennai",
    state_province:
      "Tamil Nadu",
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
    created_at:
      "2026-09-10T06:00:00Z",
    updated_at:
      "2026-09-10T06:00:00Z",
  },
];

function renderPage() {
  return render(
    <MemoryRouter
      initialEntries={[
        "/trips/1/itineraries/10/active",
      ]}
    >
      <Routes>
        <Route
          path="/trips/:tripId/itineraries/:itineraryId/active"
          element={<ActiveTripPage />}
        />
      </Routes>
    </MemoryRouter>,
  );
}

describe(
  "ActiveTripPage",
  () => {
    beforeEach(() => {
      vi.clearAllMocks();

      mockedUseItinerary.mockReturnValue({
        data: itinerary,
        isLoading: false,
        isError: false,
        error: null,
      } as ReturnType<
        typeof useItinerary
      >);

      mockedUseItineraryStops.mockReturnValue({
        data: {
          stops,
          count: stops.length,
        },
        isLoading: false,
        isError: false,
        error: null,
      } as ReturnType<
        typeof useItineraryStops
      >);

      mockedUseDestinations.mockReturnValue({
        data: {
          destinations,
          count: destinations.length,
        },
        isLoading: false,
        isError: false,
        error: null,
      } as ReturnType<
        typeof useDestinations
      >);

      mockedUseLocationTracker.mockReturnValue({
        status: "idle",
        location: null,
        error: null,
        startTracking: vi.fn(),
        stopTracking: vi.fn(),
      });
    });

    it(
      "renders the active trip",
      () => {
        renderPage();

        expect(
          screen.getByText(
            "Your trip is underway",
          ),
        ).toBeInTheDocument();

        expect(
          screen.getByText(
            "Marina Beach",
          ),
        ).toBeInTheDocument();

        expect(
          screen.getByText(
            "Kapaleeshwarar Temple",
          ),
        ).toBeInTheDocument();
      },
    );

    it(
      "shows location tracking as inactive initially",
      () => {
        renderPage();

        expect(
          screen.getByText(
            "Location tracking inactive",
          ),
        ).toBeInTheDocument();

        expect(
          screen.getByRole(
            "button",
            {
              name: "Start tracking",
            },
          ),
        ).toBeInTheDocument();
      },
    );

    it(
      "shows active tracking state",
      () => {
        mockedUseLocationTracker.mockReturnValue({
          status: "tracking",
          location: {
            latitude: 13.0499,
            longitude: 80.2824,
            accuracy: 12,
            timestamp:
              Date.now(),
          },
          error: null,
          startTracking: vi.fn(),
          stopTracking: vi.fn(),
        });

        renderPage();

        expect(
          screen.getByText(
            "Location tracking active",
          ),
        ).toBeInTheDocument();

        expect(
          screen.getByText(
            "GPS connected",
          ),
        ).toBeInTheDocument();

        expect(
          screen.getByRole(
            "button",
            {
              name: "Stop tracking",
            },
          ),
        ).toBeInTheDocument();

        expect(
          screen.getByText(
            "13.04990 , 80.28240",
          ),
        ).toBeInTheDocument();
      },
    );

    it(
      "shows location errors",
      () => {
        mockedUseLocationTracker.mockReturnValue({
          status:
            "permission_denied",
          location: null,
          error:
            "Location permission was denied.",
          startTracking: vi.fn(),
          stopTracking: vi.fn(),
        });

        renderPage();

        expect(
          screen.getByText(
            "Location permission was denied.",
          ),
        ).toBeInTheDocument();
      },
    );

    it(
      "shows the unsupported browser state",
      () => {
        mockedUseLocationTracker.mockReturnValue({
          status: "unsupported",
          location: null,
          error: null,
          startTracking: vi.fn(),
          stopTracking: vi.fn(),
        });

        renderPage();

        expect(
          screen.getByText(
            "Location tracking isn't supported",
          ),
        ).toBeInTheDocument();

        expect(
          screen.getByRole(
            "button",
            {
              name: "Start tracking",
            },
          ),
        ).toBeDisabled();
      },
    );

    it(
      "renders an invalid route state",
      () => {
        render(
          <MemoryRouter
            initialEntries={[
              "/trips/invalid/itineraries/invalid/active",
            ]}
          >
            <Routes>
              <Route
                path="/trips/:tripId/itineraries/:itineraryId/active"
                element={
                  <ActiveTripPage />
                }
              />
            </Routes>
          </MemoryRouter>,
        );

        expect(
          screen.getByText(
            "Invalid trip",
          ),
        ).toBeInTheDocument();
      },
    );
  },
);