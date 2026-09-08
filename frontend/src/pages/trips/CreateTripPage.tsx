import { FormEvent, useState } from "react";
import { Link, useNavigate } from "react-router-dom";
import axios from "axios";

import { useCreateTrip } from "../../hooks/useTrips";
import type {
  BudgetLevel,
  TransportMode,
  TripCreateRequest,
} from "../../types/trips";

function getErrorMessage(error: unknown): string {
  if (axios.isAxiosError(error)) {
    const detail = error.response?.data?.detail;

    if (typeof detail === "string") {
      return detail;
    }

    if (Array.isArray(detail)) {
      return detail
        .map((item) =>
          typeof item === "object" &&
          item !== null &&
          "msg" in item
            ? String(item.msg)
            : "Invalid input",
        )
        .join(". ");
    }
  }

  return "Unable to create your trip. Please try again.";
}

const budgetOptions: Array<{
  value: BudgetLevel;
  label: string;
}> = [
  { value: "economy", label: "Economy" },
  { value: "mid_range", label: "Mid-range" },
  { value: "luxury", label: "Luxury" },
  { value: "custom", label: "Custom" },
];

const transportOptions: Array<{
  value: TransportMode;
  label: string;
}> = [
  { value: "mixed", label: "Mixed" },
  { value: "walking", label: "Walking" },
  { value: "driving", label: "Driving" },
  { value: "public_transport", label: "Public transport" },
  { value: "bicycling", label: "Bicycling" },
  { value: "flight", label: "Flight" },
];

export default function CreateTripPage() {
  const navigate = useNavigate();
  const createTrip = useCreateTrip();

  const [title, setTitle] = useState("");
  const [description, setDescription] = useState("");
  const [startLocation, setStartLocation] = useState("");
  const [startDate, setStartDate] = useState("");
  const [startTime, setStartTime] = useState("");
  const [availableDuration, setAvailableDuration] =
    useState("");
  const [budgetLevel, setBudgetLevel] =
    useState<BudgetLevel>("mid_range");
  const [budgetAmount, setBudgetAmount] = useState("");
  const [budgetCurrency, setBudgetCurrency] =
    useState("INR");
  const [transportMode, setTransportMode] =
    useState<TransportMode>("mixed");

  const [errorMessage, setErrorMessage] = useState("");

  const handleSubmit = async (
    event: FormEvent<HTMLFormElement>,
  ) => {
    event.preventDefault();
    setErrorMessage("");

    const payload: TripCreateRequest = {
      title: title.trim(),
      description: description.trim() || null,
      start_location: startLocation.trim(),
      start_date: startDate,
      start_time: startTime || null,
      available_duration_minutes:
        availableDuration
          ? Number(availableDuration)
          : null,
      budget_level: budgetLevel,
      budget_amount: budgetAmount
        ? Number(budgetAmount)
        : null,
      budget_currency:
        budgetAmount ? budgetCurrency.trim().toUpperCase() : null,
      transport_mode: transportMode,
      status: "draft",
      is_public: false,
    };

    try {
      const trip = await createTrip.mutateAsync(payload);

      navigate(`/trips/${trip.id}`, {
        replace: true,
      });
    } catch (error) {
      setErrorMessage(getErrorMessage(error));
    }
  };

  return (
    <main className="form-page">
      <div className="form-container">
        <Link
          to="/trips"
          className="back-link"
        >
          ← Back to trips
        </Link>

        <div className="form-heading">
          <p className="page-eyebrow">
            NEW JOURNEY
          </p>

          <h1>Create a trip</h1>

          <p>
            Give Trazio the basics. We'll use them to build
            your personalized itinerary.
          </p>
        </div>

        <form
          onSubmit={handleSubmit}
          className="trip-form"
        >
          <section className="form-section">
            <div className="form-section-heading">
              <h2>Trip details</h2>
              <p>
                Tell us where and when you're going.
              </p>
            </div>

            <div className="form-grid">
              <label className="form-field form-field-full">
                Trip name
                <input
                  type="text"
                  value={title}
                  onChange={(event) =>
                    setTitle(event.target.value)
                  }
                  placeholder="Chennai weekend"
                  maxLength={100}
                  required
                />
              </label>

              <label className="form-field form-field-full">
                Starting location
                <input
                  type="text"
                  value={startLocation}
                  onChange={(event) =>
                    setStartLocation(event.target.value)
                  }
                  placeholder="Chennai"
                  maxLength={200}
                  required
                />
              </label>

              <label className="form-field">
                Start date
                <input
                  type="date"
                  value={startDate}
                  onChange={(event) =>
                    setStartDate(event.target.value)
                  }
                  required
                />
              </label>

              <label className="form-field">
                Start time
                <input
                  type="time"
                  value={startTime}
                  onChange={(event) =>
                    setStartTime(event.target.value)
                  }
                />
              </label>

              <label className="form-field form-field-full">
                Available time
                <input
                  type="number"
                  min="1"
                  value={availableDuration}
                  onChange={(event) =>
                    setAvailableDuration(
                      event.target.value,
                    )
                  }
                  placeholder="420"
                />
                <span className="field-hint">
                  Duration in minutes. Example: 420 = 7 hours.
                </span>
              </label>

              <label className="form-field form-field-full">
                Description
                <textarea
                  value={description}
                  onChange={(event) =>
                    setDescription(event.target.value)
                  }
                  placeholder="A relaxed day exploring Chennai..."
                  maxLength={10000}
                  rows={4}
                />
              </label>
            </div>
          </section>

          <section className="form-section">
            <div className="form-section-heading">
              <h2>Planning preferences</h2>
              <p>
                These guide the itinerary engine.
              </p>
            </div>

            <div className="form-grid">
              <label className="form-field">
                Budget
                <select
                  value={budgetLevel}
                  onChange={(event) =>
                    setBudgetLevel(
                      event.target.value as BudgetLevel,
                    )
                  }
                >
                  {budgetOptions.map((option) => (
                    <option
                      key={option.value}
                      value={option.value}
                    >
                      {option.label}
                    </option>
                  ))}
                </select>
              </label>

              <label className="form-field">
                Transport
                <select
                  value={transportMode}
                  onChange={(event) =>
                    setTransportMode(
                      event.target.value as TransportMode,
                    )
                  }
                >
                  {transportOptions.map((option) => (
                    <option
                      key={option.value}
                      value={option.value}
                    >
                      {option.label}
                    </option>
                  ))}
                </select>
              </label>

              <label className="form-field">
                Budget amount
                <input
                  type="number"
                  min="0"
                  step="0.01"
                  value={budgetAmount}
                  onChange={(event) =>
                    setBudgetAmount(
                      event.target.value,
                    )
                  }
                  placeholder="1500"
                />
              </label>

              <label className="form-field">
                Currency
                <input
                  type="text"
                  value={budgetCurrency}
                  onChange={(event) =>
                    setBudgetCurrency(
                      event.target.value.toUpperCase(),
                    )
                  }
                  maxLength={3}
                  placeholder="INR"
                />
              </label>
            </div>
          </section>

          {errorMessage && (
            <p
              className="auth-error"
              role="alert"
            >
              {errorMessage}
            </p>
          )}

          <div className="form-actions">
            <Link
              to="/trips"
              className="secondary-button"
            >
              Cancel
            </Link>

            <button
              type="submit"
              className="primary-button"
              disabled={createTrip.isPending}
            >
              {createTrip.isPending
                ? "Creating trip..."
                : "Create trip"}
            </button>
          </div>
        </form>
      </div>
    </main>
  );
}