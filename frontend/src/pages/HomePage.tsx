import { Link } from "react-router-dom";

import { useDestinations } from "../hooks/useDestinations";
import { useTrips } from "../hooks/useTrips";
import { getCloudinaryImageUrl } from "../lib/cloudinary";

import type { Destination } from "../types/destinations";
import type { Trip } from "../types/trips";

function formatTripDate(date: string): string {
  const parsed = new Date(date);

  if (Number.isNaN(parsed.getTime())) {
    return date;
  }

  return parsed.toLocaleDateString("en-IN", {
    day: "numeric",
    month: "short",
    year: "numeric",
  });
}

function getTripStatusLabel(status: Trip["status"]): string {
  return status.replace("_", " ");
}

function DestinationCard({
  destination,
}: {
  destination: Destination;
}) {
  const imageUrl = getCloudinaryImageUrl(
    destination.image_url,
    {
      width: 800,
      height: 500,
    },
  );

  return (
    <Link
      to={`/destinations/${destination.slug}`}
      className="home-destination-card"
    >
      <div className="home-destination-image">
        {imageUrl ? (
          <img
            src={imageUrl}
            alt={destination.name}
            loading="lazy"
          />
        ) : (
          <div className="home-destination-placeholder">
            {destination.name.charAt(0)}
          </div>
        )}

        <span className="home-destination-category">
          {destination.category}
        </span>
      </div>

      <div className="home-destination-content">
        <h3>{destination.name}</h3>

        <p>
          {destination.city ||
            destination.state_province ||
            "Chennai"}
        </p>

        <span className="home-card-link">
          Explore <span>→</span>
        </span>
      </div>
    </Link>
  );
}

function TripCard({
  trip,
}: {
  trip: Trip;
}) {
  return (
    <Link
      to={`/trips/${trip.id}`}
      className="home-trip-card"
    >
      <div className="home-trip-card-top">
        <span className="home-trip-status">
          {getTripStatusLabel(trip.status)}
        </span>

        <span className="home-trip-arrow">→</span>
      </div>

      <h3>{trip.title}</h3>

      <p className="home-trip-location">
        {trip.start_location}
      </p>

      <div className="home-trip-meta">
        <span>{formatTripDate(trip.start_date)}</span>

        <span className="home-meta-dot">•</span>

        <span>
          {trip.transport_mode.replace("_", " ")}
        </span>
      </div>
    </Link>
  );
}

export default function HomePage() {
  const {
    data: destinationsData,
    isLoading: destinationsLoading,
    isError: destinationsError,
  } = useDestinations(0, 100);

  const {
    data: tripsData,
    isLoading: tripsLoading,
    isError: tripsError,
  } = useTrips();

  const destinations = destinationsData?.destinations ?? [];
  const trips = tripsData?.trips ?? [];

  const popularDestinations = [...destinations]
    .filter((destination) => destination.is_active)
    .sort(
      (a, b) =>
        b.popularity_score - a.popularity_score,
    )
    .slice(0, 6);

  const recentTrips = [...trips]
    .sort(
      (a, b) =>
        new Date(b.updated_at).getTime() -
        new Date(a.updated_at).getTime(),
    )
    .slice(0, 3);

  return (
    <main className="home-page">
      <nav className="home-nav">
        <Link to="/home" className="home-brand">
          <span className="home-brand-mark">T</span>
          <span>TRAZIO</span>
        </Link>

        <div className="home-nav-links">
          <Link
            to="/home"
            className="home-nav-link active"
          >
            Explore
          </Link>

          <Link
            to="/trips"
            className="home-nav-link"
          >
            My Trips
          </Link>

          <Link
            to="/destinations"
            className="home-nav-link"
          >
            Destinations
          </Link>
        </div>

        <Link
          to="/trips/new"
          className="home-nav-cta"
        >
          Plan a trip
        </Link>
      </nav>

      <section className="home-hero">
        <div className="home-hero-content">
          <p className="home-eyebrow">
            SMART TRAVEL PLANNING
          </p>

          <h1>
            Plan less.
            <br />
            <span>Experience more.</span>
          </h1>

          <p className="home-hero-description">
            Build personalized journeys around your
            time, interests and budget. Trazio finds the
            best experiences and creates an optimized
            itinerary for you.
          </p>

          <div className="home-hero-actions">
            <Link
              to="/trips/new"
              className="home-primary-button"
            >
              Start planning
              <span>→</span>
            </Link>

            <Link
              to="/destinations"
              className="home-secondary-button"
            >
              Explore destinations
            </Link>
          </div>
        </div>

        <div className="home-hero-visual">
          <div className="home-hero-orbit orbit-one" />
          <div className="home-hero-orbit orbit-two" />

          <div className="home-hero-card">
            <div className="home-hero-card-header">
              <span>YOUR NEXT JOURNEY</span>
              <span className="home-live-dot" />
            </div>

            <div className="home-hero-route">
              <div className="home-route-line">
                <span className="route-point start" />
                <span className="route-point middle" />
                <span className="route-point end" />
              </div>

              <div>
                <strong>Chennai</strong>
                <span>Optimized experience</span>
              </div>
            </div>

            <div className="home-hero-stats">
              <div>
                <strong>7h</strong>
                <span>Available</span>
              </div>

              <div>
                <strong>6</strong>
                <span>Experiences</span>
              </div>

              <div>
                <strong>AI</strong>
                <span>Optimized</span>
              </div>
            </div>
          </div>
        </div>
      </section>

      <section className="home-section">
        <div className="home-section-heading">
          <div>
            <p className="home-eyebrow">
              DISCOVER
            </p>

            <h2>Places worth experiencing.</h2>

            <p>
              Explore destinations selected from
              Trazio's travel database.
            </p>
          </div>

          <Link
            to="/destinations"
            className="home-view-all"
          >
            View all destinations →
          </Link>
        </div>

        {destinationsLoading ? (
          <div className="home-destination-grid">
            {Array.from({ length: 6 }).map(
              (_, index) => (
                <div
                  key={index}
                  className="home-skeleton-card"
                />
              ),
            )}
          </div>
        ) : destinationsError ? (
          <div className="home-state-card">
            <h3>
              Destinations couldn't be loaded.
            </h3>
            <p>
              Try opening the Destinations page again.
            </p>
          </div>
        ) : (
          <div className="home-destination-grid">
            {popularDestinations.map(
              (destination) => (
                <DestinationCard
                  key={destination.id}
                  destination={destination}
                />
              ),
            )}
          </div>
        )}
      </section>

      <section className="home-trips-section">
        <div className="home-section-heading">
          <div>
            <p className="home-eyebrow">
              YOUR JOURNEYS
            </p>

            <h2>Pick up where you left off.</h2>

            <p>
              Continue planning your recent Trazio
              experiences.
            </p>
          </div>

          <Link
            to="/trips"
            className="home-view-all"
          >
            View all trips →
          </Link>
        </div>

        {tripsLoading ? (
          <div className="home-trip-grid">
            {Array.from({ length: 3 }).map(
              (_, index) => (
                <div
                  key={index}
                  className="home-trip-skeleton"
                />
              ),
            )}
          </div>
        ) : tripsError ? (
          <div className="home-state-card">
            <h3>
              We couldn't load your trips.
            </h3>

            <p>
              Your destinations are still available
              above.
            </p>
          </div>
        ) : recentTrips.length === 0 ? (
          <div className="home-empty-trips">
            <div>
              <span className="home-empty-icon">
                +
              </span>
            </div>

            <div>
              <h3>Your next journey starts here.</h3>

              <p>
                Create a trip and let Trazio build an
                optimized experience around you.
              </p>
            </div>

            <Link
              to="/trips/new"
              className="home-primary-button"
            >
              Create a trip →
            </Link>
          </div>
        ) : (
          <div className="home-trip-grid">
            {recentTrips.map((trip) => (
              <TripCard
                key={trip.id}
                trip={trip}
              />
            ))}
          </div>
        )}
      </section>

      <section className="home-final-cta">
        <div>
          <p className="home-eyebrow">
            READY TO GO?
          </p>

          <h2>
            Your next experience is waiting.
          </h2>

          <p>
            Tell Trazio what you want from your day.
            We'll figure out the route.
          </p>
        </div>

        <Link
          to="/trips/new"
          className="home-primary-button"
        >
          Plan my trip →
        </Link>
      </section>

      <footer className="home-footer">
        <span>TRAZIO</span>

        <span>
          Intelligent travel planning · Chennai
        </span>
      </footer>
    </main>
  );
}