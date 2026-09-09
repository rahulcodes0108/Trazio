import { render, screen } from "@testing-library/react";
import { MemoryRouter } from "react-router-dom";
import { beforeEach, describe, expect, it, vi } from "vitest";
import DestinationDetailPage from "./DestinationDetailPage";
import type { Destination } from "../../types/destinations";

const { mockedUseDestinationBySlug } = vi.hoisted(() => ({
  mockedUseDestinationBySlug: vi.fn(),
}));

vi.mock("../../hooks/useDestinations", () => ({
  useDestinationBySlug: mockedUseDestinationBySlug,
}));

const baseDestination: Destination = {
  id: 1,
  name: "Marina Beach",
  slug: "marina-beach",
  description:
    "A famous Chennai beach known for its long coastline and lively atmosphere.",
  image_url: "https://example.com/marina-beach.jpg",
  category: "beach",
  location: "POINT(80.2824 13.0500)",
  address_line1: "Marina Beach Road",
  address_line2: null,
  city: "Chennai",
  state_province: "Tamil Nadu",
  postal_code: null,
  country: "India",
  opening_hours: "05:00-21:00",
  entry_fee: 0,
  entry_fee_currency: "INR",
  average_visit_duration_minutes: 90,
  accessibility: "moderate",
  accessibility_notes:
    "Wheelchair access available in selected areas.",
  popularity_score: 92,
  is_active: true,
  website_url: "https://example.com/marina",
  phone_number: "+919999999999",
  email: "info@example.com",
  created_at: "2026-09-01T10:00:00Z",
  updated_at: "2026-09-01T10:00:00Z",
};

function renderPage() {
  return render(
    <MemoryRouter
      initialEntries={["/destinations/marina-beach"]}
    >
      <DestinationDetailPage />
    </MemoryRouter>,
  );
}

describe("DestinationDetailPage", () => {
  beforeEach(() => {
    mockedUseDestinationBySlug.mockReset();
  });

  it("shows the loading state", () => {
    mockedUseDestinationBySlug.mockReturnValue({
      data: undefined,
      isLoading: true,
      isError: false,
      refetch: vi.fn(),
    });

    renderPage();

    expect(
      screen.getByText("Loading destination..."),
    ).toBeInTheDocument();
  });

  it("shows the error state when the destination cannot be loaded", () => {
    const refetch = vi.fn();

    mockedUseDestinationBySlug.mockReturnValue({
      data: undefined,
      isLoading: false,
      isError: true,
      refetch,
    });

    renderPage();

    expect(
      screen.getByRole("heading", {
        name: "Destination unavailable",
      }),
    ).toBeInTheDocument();

    expect(
      screen.getByText(
        /We couldn't load this destination/i,
      ),
    ).toBeInTheDocument();

    expect(
      screen.getByRole("button", {
        name: "Try again",
      }),
    ).toBeInTheDocument();

    expect(
      screen.getByRole("link", {
        name: /Back to destinations/i,
      }),
    ).toHaveAttribute("href", "/destinations");
  });

  it("renders the destination details successfully", () => {
    mockedUseDestinationBySlug.mockReturnValue({
      data: baseDestination,
      isLoading: false,
      isError: false,
      refetch: vi.fn(),
    });

    renderPage();

    expect(
      screen.getByRole("heading", {
        name: "Marina Beach",
      }),
    ).toBeInTheDocument();

    expect(
      screen.getByText("Beach"),
    ).toBeInTheDocument();

    expect(
      screen.getByText("Chennai, Tamil Nadu"),
    ).toBeInTheDocument();

    expect(
      screen.getByText(baseDestination.description!),
    ).toBeInTheDocument();

    expect(
      screen.getByText("90 min"),
    ).toBeInTheDocument();

    expect(
      screen.getByText("₹0"),
    ).toBeInTheDocument();

    expect(
      screen.getByText("Moderate"),
    ).toBeInTheDocument();

    expect(
      screen.getByText("05:00-21:00"),
    ).toBeInTheDocument();

    expect(
      screen.getByText(
        /Wheelchair access available in selected areas/i,
      ),
    ).toBeInTheDocument();
  });

  it("renders the category fallback when image_url is null", () => {
  const destinationWithoutImage: Destination = {
    ...baseDestination,
    image_url: null,
  };

  mockedUseDestinationBySlug.mockReturnValue({
    data: destinationWithoutImage,
    isLoading: false,
    isError: false,
    refetch: vi.fn(),
  });

  renderPage();

  expect(
    screen.queryByRole("img", {
      name: "Marina Beach",
    }),
  ).not.toBeInTheDocument();

  const fallback = document.querySelector(
    ".destination-detail-image-fallback",
  );

  expect(fallback).toBeInTheDocument();
  expect(fallback).toHaveTextContent("Beach");
});

  it("links to the trip creation flow with the destination id", () => {
    mockedUseDestinationBySlug.mockReturnValue({
      data: baseDestination,
      isLoading: false,
      isError: false,
      refetch: vi.fn(),
    });

    renderPage();

    const addToTripLink = screen.getByRole("link", {
      name: "Add to trip",
    });

    expect(addToTripLink).toHaveAttribute(
      "href",
      "/trips/new?destination=1",
    );
  });

  it("renders contact links when contact information is available", () => {
    mockedUseDestinationBySlug.mockReturnValue({
      data: baseDestination,
      isLoading: false,
      isError: false,
      refetch: vi.fn(),
    });

    renderPage();

    expect(
      screen.getByRole("link", {
        name: "Visit website",
      }),
    ).toHaveAttribute(
      "href",
      "https://example.com/marina",
    );

    expect(
      screen.getByRole("link", {
        name: "+919999999999",
      }),
    ).toHaveAttribute(
      "href",
      "tel:+919999999999",
    );

    expect(
      screen.getByRole("link", {
        name: "info@example.com",
      }),
    ).toHaveAttribute(
      "href",
      "mailto:info@example.com",
    );
  });
});