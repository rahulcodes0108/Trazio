import { Link, useNavigate, useParams } from "react-router-dom";
import axios from "axios";

import {
  useDeleteTrip,
  useTrip,
} from "../../hooks/useTrips";

import {
  useGenerateItinerary,
  useItineraries,
} from "../../hooks/useItineraries";

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

  if (error instanceof Error) {
    return error.message;
  }

  return "Unable to complete this request.";
}

function formatItineraryStatus(status: string): string {
  return status.replace(/_/g, " ");
}

function formatCost(
  amount: number,
  currency: string | null,
): string {
  if (currency) {
    return `${currency} ${amount}`;
  }

  return `${amount}`;
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

  const {
    data: itineraryData,
    isLoading: isItinerariesLoading,
    isError: isItinerariesError,
    error: itinerariesError,
  } = useItineraries(parsedTripId);

  const generateItinerary = useGenerateItinerary(parsedTripId);

  /*
   * The backend returns itineraries ordered by version.
   * We still explicitly select the highest version so the UI
   * remains correct even if the backend ordering changes.
   */
  const latestItinerary =
    itineraryData?.itineraries?.reduce(
      (latest, itinerary) => {
        if (!latest || itinerary.version > latest.version) {
          return itinerary;
        }

        return latest;
      },
      null as (typeof itineraryData.itineraries[number] | null),
    ) ?? null;

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

  const handleGenerateItinerary = async () => {
    try {
      await generateItinerary.mutateAsync();
    } catch {
      // The mutation error is displayed in the UI below.
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

            <Link
              to="/trips"
              className="primary-button"
            >
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
              <Link
                to="/trips"
                className="secondary-button"
              >
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
        <Link
          to="/trips"
          className="back-link"
        >
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
            <p className="detail-label">
              STARTING POINT
            </p>

            <h2>{trip.start_location}</h2>
          </article>

          <article className="detail-card">
            <p className="detail-label">DATE</p>

            <h2>{trip.start_date}</h2>
          </article>

          <article className="detail-card">
            <p className="detail-label">
              AVAILABLE TIME
            </p>

            <h2>
              {formatDuration(
                trip.available_duration_minutes,
              )}
            </h2>
          </article>

          <article className="detail-card">
            <p className="detail-label">
              TRANSPORT
            </p>

            <h2>
              {trip.transport_mode.replace(/_/g, " ")}
            </h2>
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
            <p className="detail-label">
              START TIME
            </p>

            <h2>
              {trip.start_time ?? "Not specified"}
            </h2>
          </article>
        </section>

        {trip.description && (
          <section className="detail-section">
            <p className="detail-label">
              ABOUT THIS TRIP
            </p>

            <p className="detail-description">
              {trip.description}
            </p>
          </section>
        )}

        <section className="planning-card">
          <div>
            <p className="detail-label">
              {latestItinerary
                ? "ITINERARY"
                : "READY TO PLAN?"}
            </p>

            <h2>
              {latestItinerary
                ? `Your itinerary · Version ${latestItinerary.version}`
                : "Turn this trip into an itinerary."}
            </h2>

            <p>
              {latestItinerary
                ? latestItinerary.notes ??
                  "Your itinerary has been generated using your trip requirements, destination intelligence and routing constraints."
                : "Trazio will use your trip requirements, destination intelligence and routing constraints to build the best possible plan."}
            </p>

            {isItinerariesLoading && (
              <p className="page-muted">
                Loading itinerary...
              </p>
            )}

            {isItinerariesError && (
              <p className="error-message">
                {getErrorMessage(itinerariesError)}
              </p>
            )}

            {generateItinerary.isError && (
              <p className="error-message">
                {getErrorMessage(
                  generateItinerary.error,
                )}
              </p>
            )}

            {latestItinerary && (
              <div className="itinerary-summary">
                <div className="itinerary-summary-header">
                  <div>
                    <span className="page-eyebrow">
                      LATEST VERSION
                    </span>

                    <h3>
                      Version {latestItinerary.version}
                    </h3>
                  </div>

                  <span
                    className={`trip-status status-${latestItinerary.status}`}
                  >
                    {formatItineraryStatus(
                      latestItinerary.status,
                    )}
                  </span>
                </div>

                <div className="itinerary-stats">
                  <div>
                    <strong>
                      {latestItinerary.stop_count}
                    </strong>

                    <span>Stops</span>
                  </div>
                  <div className="itinerary-summary-actions">
                  <Link
                    to={`/itineraries/${latestItinerary.id}`}
                    className="secondary-button"
                  >
                    View itinerary
                  </Link>
                </div>

                  <div>
                    <strong>
                      {formatDuration(
                        latestItinerary.total_duration_minutes,
                      )}
                    </strong>

                    <span>Total time</span>
                  </div>

                  <div>
                    <strong>
                      {formatDuration(
                        latestItinerary.estimated_travel_duration_minutes,
                      )}
                    </strong>

                    <span>Travel</span>
                  </div>

                  <div>
                    <strong>
                      {formatCost(
                        latestItinerary.estimated_cost,
                        latestItinerary.estimated_cost_currency,
                      )}
                    </strong>

                    <span>Estimated cost</span>
                  </div>
                </div>
              </div>
            )}
          </div>

          <button
            type="button"
            className="primary-button"
            onClick={() =>
              void handleGenerateItinerary()
            }
            disabled={generateItinerary.isPending}
          >
            {generateItinerary.isPending
              ? "Generating itinerary..."
              : latestItinerary
                ? "Regenerate itinerary"
                : "Generate itinerary"}
          </button>
        </section>
      </div>
    </main>
  );
}