import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { fireEvent, render, screen } from "@testing-library/react";
import { MemoryRouter } from "react-router-dom";
import { beforeEach, describe, expect, it, vi } from "vitest";
import DestinationsPage from "./DestinationsPage";

const mockUseDestinations = vi.fn();

vi.mock("../../hooks/useDestinations", () => ({
  useDestinations: () => mockUseDestinations(),
}));

const destinations = [
  {
    id: 1,
    name: "Marina Beach",
    slug: "marina-beach",
    description: "A famous Chennai beach.",
    category: "beach",
    location: "POINT(80.2824 13.0500)",
    address_line1: null,
    address_line2: null,
    city: "Chennai",
    state_province: "Tamil Nadu",
    postal_code: null,
    country: "India",
    opening_hours: null,
    entry_fee: null,
    entry_fee_currency: null,
    average_visit_duration_minutes: 120,
    accessibility: "good",
    accessibility_notes: null,
    popularity_score: 95,
    is_active: true,
    website_url: null,
    phone_number: null,
    email: null,
    created_at: "2026-01-01T00:00:00Z",
    updated_at: "2026-01-01T00:00:00Z",
  },
  {
    id: 2,
    name: "Guindy National Park",
    slug: "guindy-national-park",
    description: "A green urban national park.",
    category: "nature",
    location: "POINT(80.2376 13.0068)",
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
    accessibility: "moderate",
    accessibility_notes: null,
    popularity_score: 82,
    is_active: true,
    website_url: null,
    phone_number: null,
    email: null,
    created_at: "2026-01-01T00:00:00Z",
    updated_at: "2026-01-01T00:00:00Z",
  },
];

function renderPage() {
  const queryClient = new QueryClient();

  return render(
    <QueryClientProvider client={queryClient}>
      <MemoryRouter>
        <DestinationsPage />
      </MemoryRouter>
    </QueryClientProvider>,
  );
}

describe("DestinationsPage", () => {
  beforeEach(() => {
    mockUseDestinations.mockReset();
    mockUseDestinations.mockReturnValue({
      data: {
        destinations,
        count: destinations.length,
      },
      isLoading: false,
      isError: false,
      refetch: vi.fn(),
    });
  });

  it("renders destinations from the API", () => {
    renderPage();

    expect(screen.getByText("Marina Beach")).toBeInTheDocument();
    expect(
      screen.getByText("Guindy National Park"),
    ).toBeInTheDocument();
  });

  it("filters destinations using local search", () => {
    renderPage();

    fireEvent.change(
      screen.getByPlaceholderText("Search destinations..."),
      {
        target: { value: "marina" },
      },
    );

    expect(screen.getByText("Marina Beach")).toBeInTheDocument();
    expect(
      screen.queryByText("Guindy National Park"),
    ).not.toBeInTheDocument();
  });

  it("filters destinations by category", () => {
    renderPage();

    fireEvent.click(screen.getByRole("button", { name: "Nature" }));

    expect(
      screen.getByText("Guindy National Park"),
    ).toBeInTheDocument();

    expect(
      screen.queryByText("Marina Beach"),
    ).not.toBeInTheDocument();
  });

  it("shows an empty state when no destinations match", () => {
    renderPage();

    fireEvent.change(
      screen.getByPlaceholderText("Search destinations..."),
      {
        target: { value: "does-not-exist" },
      },
    );

    expect(
      screen.getByText("No destinations found."),
    ).toBeInTheDocument();
  });

  it("shows loading state", () => {
    mockUseDestinations.mockReturnValue({
      data: undefined,
      isLoading: true,
      isError: false,
      refetch: vi.fn(),
    });

    renderPage();

    expect(
      screen.getByText("Discovering destinations..."),
    ).toBeInTheDocument();
  });

  it("shows error state and retry action", () => {
    const refetch = vi.fn();

    mockUseDestinations.mockReturnValue({
      data: undefined,
      isLoading: false,
      isError: true,
      refetch,
    });

    renderPage();

    expect(
      screen.getByText("We couldn't load destinations."),
    ).toBeInTheDocument();

    fireEvent.click(screen.getByRole("button", { name: "Try again" }));

    expect(refetch).toHaveBeenCalledTimes(1);
  });
});