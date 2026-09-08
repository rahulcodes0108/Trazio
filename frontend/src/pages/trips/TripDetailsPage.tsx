import { Link, useNavigate, useParams } from "react-router-dom";
import axios from "axios";

import {
  useDeleteTrip,
  useTrip,
} from "../../hooks/useTrips";

function formatDuration(minutes: number | null): string {
  if (!minutes) {
    return "Not specified";
  }

  const hours = Math.floor(minutes / 60);
  const remainingMinutes = minutes % 60;

  if (hours === 0) {
    return `${remainingMinutes} min`;
  }

  if (remainingMinutes === 0) {
    return `${hours} hr`;
  }

  return `${hours} hr ${remainingMinutes} min`;
}

function getErrorMessage(error: unknown): string {
  if (axios.isAxiosError(error)) {
    const detail = error.response?.data?.detail;

    if (typeof detail === "string") {
      return detail;
    }
  }

  return "Unable to delete this trip.";
}

export default function TripDetailsPage() {
  const navigate = useNavigate();
  const { tripId } = useParams();

  const parsedTripId = Number(tripId);

  const {
    data: trip,
    isLoading,
    isError,
    refetch,
  } = useTrip(parsedTripId);

  const deleteTrip = useDeleteTrip();

  const handleDelete = async () => {
    if (!trip) {
      return;
    }

    const confirmed = window.confirm(
      `Delete "${trip.title}"? This action cannot be undone.`,
    );

    if (!confirmed) {
      return;
    }

    try {
      await deleteTrip.mutateAsync(trip.id);
      navigate("/trips", { replace: true });
    } catch (error) {
      window.alert(getErrorMessage(error));
    }
  };

  if (!Number.isFinite(parsedTripId) || parsedTripId <= 0) {
    return (
      <main className="trips-page">
        <div className="trips-container">
          <div className="state-card">
            <h2>Invalid trip</h2>
            <p>
              The trip you're looking for doesn't have a valid ID.
            </p>
            <Link to="/trips" className="primary-button">
              Back to trips
            </Link>
          </div>
        </div>
      </main>
    );
  }

  if (isLoading) {
    return (
      <main className="trips-page">
        <div className="trips-container">
          <p className="page-eyebrow">TRIP</p>
          <h1>Loading trip...</h1>
        </div>
      </main>
    );
  }

  if (isError || !trip) {
    return (
      <main className="trips-page">
        <div className="trips-container">
          <div className="state-card">
            <h2>Trip unavailable</h2>
            <p>
              We couldn't load this trip. It may have been
              removed or you may no longer have access to it.
            </p>

            <div className="form-actions">
              <Link to="/trips" className="secondary-button">
                Back to trips
              </Link>

              <button
                type="button"
                onClick={() => void refetch()}
              >
                Try again
              </button>
            </div>
          </div>
        </div>
      </main>
    );
  }

  return (
    <main className="trips-page">
      <div className="trips-container">
        <Link to="/trips" className="back-link">
          ← Back to trips
        </Link>

        <header className="trip-detail-header">
          <div>
            <span className="trip-status">
              {trip.status}
            </span>

            <p className="page-eyebrow">
              YOUR JOURNEY
            </p>

            <h1>{trip.title}</h1>

            <p className="page-muted">
              {trip.start_location} · {trip.start_date}
            </p>
          </div>

          <div className="trip-detail-actions">
            <Link
              to={`/trips/${trip.id}/edit`}
              className="secondary-button"
            >
              Edit trip
            </Link>

            <button
              type="button"
              className="danger-button"
              onClick={() => void handleDelete()}
              disabled={deleteTrip.isPending}
            >
              {deleteTrip.isPending
                ? "Deleting..."
                : "Delete"}
            </button>
          </div>
        </header>

        <section className="trip-detail-grid">
          <article className="detail-card">
            <p className="detail-label">STARTING POINT</p>
            <h2>{trip.start_location}</h2>
          </article>

          <article className="detail-card">
            <p className="detail-label">DATE</p>
            <h2>{trip.start_date}</h2>
          </article>

          <article className="detail-card">
            <p className="detail-label">AVAILABLE TIME</p>
            <h2>
              {formatDuration(
                trip.available_duration_minutes,
              )}
            </h2>
          </article>

          <article className="detail-card">
            <p className="detail-label">TRANSPORT</p>
            <h2>{trip.transport_mode.replace(/_/g, " ")}</h2>
          </article>

          <article className="detail-card">
            <p className="detail-label">BUDGET</p>
            <h2>
              {trip.budget_amount !== null &&
              trip.budget_amount !== undefined
                ? `${trip.budget_currency ?? ""} ${trip.budget_amount}`
                : trip.budget_level.replace(/_/g, " ")}
            </h2>
          </article>

          <article className="detail-card">
            <p className="detail-label">START TIME</p>
            <h2>{trip.start_time ?? "Not specified"}</h2>
          </article>
        </section>

        {trip.description && (
          <section className="detail-section">
            <p className="detail-label">ABOUT THIS TRIP</p>
            <p className="detail-description">
              {trip.description}
            </p>
          </section>
        )}

        <section className="planning-card">
          <div>
            <p className="detail-label">
              READY TO PLAN?
            </p>

            <h2>
              Turn this trip into an itinerary.
            </h2>

            <p>
              Trazio will use your trip requirements,
              destination intelligence and routing
              constraints to build the best possible plan.
            </p>
          </div>

          <button
            type="button"
            className="primary-button"
            disabled
          >
            Generate itinerary
          </button>
        </section>
      </div>
    </main>
  );
}