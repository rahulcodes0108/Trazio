import { render, screen } from "@testing-library/react";
import { describe, expect, it, vi } from "vitest";
import { MemoryRouter } from "react-router-dom";
import TripDetailsPage from "./TripDetailsPage";

const mockTrip = {
  id: 1,
  user_id: 10,
  title: "Chennai Day Trip",
  description: "Explore Chennai in one day.",
  start_location: "Chennai Central",
  start_date: "2026-09-15",
  start_time: "09:00:00",
  end_date: null,
  end_time: null,
  available_duration_minutes: 420,
  budget_level: "mid_range" as const,
  budget_amount: 1500,
  budget_currency: "INR",
  transport_mode: "mixed" as const,
  preferences: null,
  status: "draft" as const,
  is_public: false,
  share_token: null,
  created_at: "2026-09-01T10:00:00Z",
  updated_at: "2026-09-01T10:00:00Z",
};

const mockUseTrip = vi.fn();
const mockUseDeleteTrip = vi.fn();

vi.mock("../../hooks/useTrips", () => ({
  useTrip: (...args: unknown[]) => mockUseTrip(...args),
  useDeleteTrip: () => mockUseDeleteTrip(),
}));

vi.mock("react-router-dom", async () => {
  const actual = await vi.importActual<typeof import("react-router-dom")>(
    "react-router-dom",
  );

  return {
    ...actual,
    useParams: () => ({ tripId: "1" }),
    useNavigate: () => vi.fn(),
  };
});

function renderPage() {
  return render(
    <MemoryRouter initialEntries={["/trips/1"]}>
      <TripDetailsPage />
    </MemoryRouter>,
  );
}

describe("TripDetailsPage", () => {
  it("renders the trip details", () => {
    mockUseTrip.mockReturnValue({
      data: mockTrip,
      isLoading: false,
      isError: false,
      refetch: vi.fn(),
    });

    mockUseDeleteTrip.mockReturnValue({
      mutateAsync: vi.fn(),
      isPending: false,
    });

    renderPage();

    expect(
      screen.getByRole("heading", {
        name: "Chennai Day Trip",
      }),
    ).toBeInTheDocument();

    expect(screen.getByText("Chennai Central")).toBeInTheDocument();
    expect(
      screen.getByText("Explore Chennai in one day."),
    ).toBeInTheDocument();
  });

  it("renders the loading state", () => {
    mockUseTrip.mockReturnValue({
      data: undefined,
      isLoading: true,
      isError: false,
      refetch: vi.fn(),
    });

    mockUseDeleteTrip.mockReturnValue({
      mutateAsync: vi.fn(),
      isPending: false,
    });

    renderPage();

    expect(screen.getByText(/loading trip/i)).toBeInTheDocument();
  });

  it("renders the error state", () => {
    mockUseTrip.mockReturnValue({
      data: undefined,
      isLoading: false,
      isError: true,
      refetch: vi.fn(),
    });

    mockUseDeleteTrip.mockReturnValue({
      mutateAsync: vi.fn(),
      isPending: false,
    });

    renderPage();

    expect(
      screen.getByRole("heading", {
        name: /trip unavailable/i,
      }),
    ).toBeInTheDocument();
  });

  it("provides an edit link", () => {
    mockUseTrip.mockReturnValue({
      data: mockTrip,
      isLoading: false,
      isError: false,
      refetch: vi.fn(),
    });

    mockUseDeleteTrip.mockReturnValue({
      mutateAsync: vi.fn(),
      isPending: false,
    });

    renderPage();

    expect(
      screen.getByRole("link", {
        name: /edit/i,
      }),
    ).toHaveAttribute("href", "/trips/1/edit");
  });

  it("keeps itinerary generation disabled", () => {
    mockUseTrip.mockReturnValue({
      data: mockTrip,
      isLoading: false,
      isError: false,
      refetch: vi.fn(),
    });

    mockUseDeleteTrip.mockReturnValue({
      mutateAsync: vi.fn(),
      isPending: false,
    });

    renderPage();

    expect(
      screen.getByRole("button", {
        name: /generate itinerary/i,
      }),
    ).toBeDisabled();
  });
});