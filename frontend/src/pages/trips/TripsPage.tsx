import { Link } from "react-router-dom";

import { useTrips } from "../../hooks/useTrips";

export default function TripsPage() {
  const { data, isLoading, isError, refetch } = useTrips();

  if (isLoading) {
    return (
      <main className="trips-page">
        <div className="trips-container">
          <p className="page-eyebrow">YOUR JOURNEYS</p>
          <h1>Your trips</h1>
          <p className="page-muted">Loading your trips...</p>
        </div>
      </main>
    );
  }

  if (isError) {
    return (
      <main className="trips-page">
        <div className="trips-container">
          <p className="page-eyebrow">YOUR JOURNEYS</p>
          <h1>Your trips</h1>

          <div className="state-card">
            <h2>We couldn't load your trips.</h2>
            <p>
              Check your connection and try again.
            </p>

            <button
              type="button"
              onClick={() => void refetch()}
            >
              Try again
            </button>
          </div>
        </div>
      </main>
    );
  }

  const trips = data?.trips ?? [];

  return (
    <main className="trips-page">
      <div className="trips-container">
        <header className="trips-header">
          <div>
            <p className="page-eyebrow">YOUR JOURNEYS</p>
            <h1>Your trips</h1>
            <p className="page-muted">
              Plan, manage and revisit your Trazio journeys.
            </p>
          </div>

          <Link
            to="/trips/new"
            className="primary-button"
          >
            + Create trip
          </Link>
        </header>

        {trips.length === 0 ? (
          <section className="empty-state">
            <div className="empty-icon">✦</div>

            <h2>Your next adventure starts here.</h2>

            <p>
              Tell Trazio where you're going, how much time
              you have and what you enjoy. We'll take it from
              there.
            </p>

            <Link
              to="/trips/new"
              className="primary-button"
            >
              Create your first trip
            </Link>
          </section>
        ) : (
          <section className="trip-grid">
            {trips.map((trip) => (
              <Link
                key={trip.id}
                to={`/trips/${trip.id}`}
                className="trip-card"
              >
                <div className="trip-card-top">
                  <span className="trip-status">
                    {trip.status}
                  </span>

                  <span className="trip-arrow">
                    →
                  </span>
                </div>

                <h2>{trip.title}</h2>

                <p className="trip-location">
                  {trip.start_location}
                </p>

                <div className="trip-meta">
                  <span>{trip.start_date}</span>
                  <span>•</span>
                  <span>{trip.transport_mode}</span>
                </div>

                {trip.description && (
                  <p className="trip-description">
                    {trip.description}
                  </p>
                )}
              </Link>
            ))}
          </section>
        )}
      </div>
    </main>
  );
}