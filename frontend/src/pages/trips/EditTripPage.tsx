import { FormEvent, useEffect, useState } from "react";
import { Link, useNavigate, useParams } from "react-router-dom";
import { useTrip, useUpdateTrip } from "../../hooks/useTrips";
import type {
  BudgetLevel,
  TransportMode,
  TripUpdateRequest,
} from "../../types/trips";

function EditTripPage() {
  const { tripId } = useParams();
  const navigate = useNavigate();

  const id = Number(tripId);
  const { data: trip, isLoading, isError, refetch } = useTrip(id);
  const updateTrip = useUpdateTrip();

  const [title, setTitle] = useState("");
  const [startLocation, setStartLocation] = useState("");
  const [startDate, setStartDate] = useState("");
  const [startTime, setStartTime] = useState("");
  const [availableDuration, setAvailableDuration] = useState("");
  const [description, setDescription] = useState("");
  const [budgetLevel, setBudgetLevel] =
    useState<BudgetLevel>("mid_range");
  const [transportMode, setTransportMode] =
    useState<TransportMode>("mixed");
  const [budgetAmount, setBudgetAmount] = useState("");
  const [budgetCurrency, setBudgetCurrency] = useState("INR");
  const [error, setError] = useState("");

  useEffect(() => {
    if (!trip) {
      return;
    }

    setTitle(trip.title);
    setStartLocation(trip.start_location);
    setStartDate(trip.start_date);
    setStartTime(trip.start_time ?? "");
    setAvailableDuration(
      trip.available_duration_minutes?.toString() ?? "",
    );
    setDescription(trip.description ?? "");
    setBudgetLevel(trip.budget_level);
    setTransportMode(trip.transport_mode);
    setBudgetAmount(trip.budget_amount?.toString() ?? "");
    setBudgetCurrency(trip.budget_currency ?? "INR");
  }, [trip]);

  if (!Number.isFinite(id) || id <= 0) {
    return (
      <main className="page-shell">
        <section className="empty-state">
          <h1>Invalid trip</h1>
          <p>The requested trip could not be identified.</p>
          <Link to="/trips" className="button button-primary">
            Back to trips
          </Link>
        </section>
      </main>
    );
  }

  if (isLoading) {
    return (
      <main className="page-shell">
        <section className="loading-state">
          <p>Loading trip...</p>
        </section>
      </main>
    );
  }

  if (isError || !trip) {
    return (
      <main className="page-shell">
        <section className="empty-state">
          <h1>Trip unavailable</h1>
          <p>We couldn't load this trip.</p>

          <div className="empty-state-actions">
            <button
              type="button"
              className="button button-secondary"
              onClick={() => refetch()}
            >
              Try again
            </button>

            <Link to="/trips" className="button button-primary">
              Back to trips
            </Link>
          </div>
        </section>
      </main>
    );
  }

  const handleSubmit = async (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault();
    setError("");

    const payload: TripUpdateRequest = {
      title: title.trim(),
      start_location: startLocation.trim(),
      start_date: startDate,
      start_time: startTime || null,
      available_duration_minutes: availableDuration
        ? Number(availableDuration)
        : null,
      description: description.trim() || null,
      budget_level: budgetLevel,
      transport_mode: transportMode,
      budget_amount: budgetAmount ? Number(budgetAmount) : null,
      budget_currency: budgetCurrency.trim().toUpperCase() || null,
    };

    try {
      await updateTrip.mutateAsync({
        tripId: id,
        payload,
      });

      navigate(`/trips/${id}`);
    } catch (err) {
      const message =
        err &&
        typeof err === "object" &&
        "response" in err &&
        typeof err.response === "object" &&
        err.response !== null &&
        "data" in err.response &&
        typeof err.response.data === "object" &&
        err.response.data !== null &&
        "detail" in err.response.data
          ? String(err.response.data.detail)
          : "Unable to update the trip. Please try again.";

      setError(message);
    }
  };

  return (
    <main className="page-shell">
      <section className="form-page">
        <div className="page-heading">
          <div>
            <Link to={`/trips/${id}`} className="back-link">
              ← Back to trip
            </Link>

            <h1>Edit trip</h1>
            <p>Update your trip details and planning preferences.</p>
          </div>
        </div>

        <form className="trip-form" onSubmit={handleSubmit}>
          {error && (
            <div className="form-error" role="alert">
              {error}
            </div>
          )}

          <label>
            Trip title
            <input
              value={title}
              onChange={(event) => setTitle(event.target.value)}
              required
              minLength={1}
              maxLength={100}
            />
          </label>

          <label>
            Starting location
            <input
              value={startLocation}
              onChange={(event) =>
                setStartLocation(event.target.value)
              }
              required
              minLength={1}
              maxLength={200}
            />
          </label>

          <div className="form-grid">
            <label>
              Start date
              <input
                type="date"
                value={startDate}
                onChange={(event) => setStartDate(event.target.value)}
                required
              />
            </label>

            <label>
              Start time
              <input
                type="time"
                value={startTime}
                onChange={(event) => setStartTime(event.target.value)}
              />
            </label>
          </div>

          <label>
            Available duration
            <input
              type="number"
              min="1"
              value={availableDuration}
              onChange={(event) =>
                setAvailableDuration(event.target.value)
              }
              placeholder="Minutes"
            />
          </label>

          <label>
            Description
            <textarea
              value={description}
              onChange={(event) => setDescription(event.target.value)}
              rows={5}
              maxLength={10000}
            />
          </label>

          <div className="form-grid">
            <label>
              Budget
              <select
                value={budgetLevel}
                onChange={(event) =>
                  setBudgetLevel(event.target.value as BudgetLevel)
                }
              >
                <option value="economy">Economy</option>
                <option value="mid_range">Mid-range</option>
                <option value="luxury">Luxury</option>
                <option value="custom">Custom</option>
              </select>
            </label>

            <label>
              Transport
              <select
                value={transportMode}
                onChange={(event) =>
                  setTransportMode(
                    event.target.value as TransportMode,
                  )
                }
              >
                <option value="walking">Walking</option>
                <option value="driving">Driving</option>
                <option value="public_transport">
                  Public transport
                </option>
                <option value="bicycling">Bicycling</option>
                <option value="flight">Flight</option>
                <option value="mixed">Mixed</option>
              </select>
            </label>
          </div>

          <div className="form-grid">
            <label>
              Budget amount
              <input
                type="number"
                min="0"
                value={budgetAmount}
                onChange={(event) =>
                  setBudgetAmount(event.target.value)
                }
              />
            </label>

            <label>
              Currency
              <input
                value={budgetCurrency}
                onChange={(event) =>
                  setBudgetCurrency(event.target.value.toUpperCase())
                }
                maxLength={3}
              />
            </label>
          </div>

          <div className="form-actions">
            <Link
              to={`/trips/${id}`}
              className="button button-secondary"
            >
              Cancel
            </Link>

            <button
              type="submit"
              className="button button-primary"
              disabled={updateTrip.isPending}
            >
              {updateTrip.isPending ? "Saving..." : "Save changes"}
            </button>
          </div>
        </form>
      </section>
    </main>
  );
}

export default EditTripPage;