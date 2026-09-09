import { Link, useParams } from "react-router-dom";

import { useDestinationBySlug } from "../../hooks/useDestinations";
import { getCloudinaryImageUrl } from "../../lib/cloudinary";
import type { Destination } from "../../types/destinations";

function formatCategory(category: string): string {
  return category
    .replace(/_/g, " ")
    .replace(/\b\w/g, (letter) => letter.toUpperCase());
}

function formatLocation(destination: Destination): string {
  return (
    [destination.city, destination.state_province]
      .filter(Boolean)
      .join(", ") ||
    destination.location ||
    "Location unavailable"
  );
}

function formatFee(destination: Destination): string {
  if (destination.entry_fee === null) {
    return "Not specified";
  }

  const currency = destination.entry_fee_currency || "INR";

  return new Intl.NumberFormat("en-IN", {
    style: "currency",
    currency,
    maximumFractionDigits: 0,
  }).format(destination.entry_fee);
}

export default function DestinationDetailPage() {
  const { slug } = useParams<{ slug: string }>();

  const {
    data: destination,
    isLoading,
    isError,
    refetch,
  } = useDestinationBySlug(slug ?? "");

  if (isLoading) {
    return (
      <main className="destination-detail-page">
        <section
          className="destination-detail-state"
          aria-live="polite"
        >
          <div
            className="loading-spinner"
            aria-hidden="true"
          />
          <p>Loading destination...</p>
        </section>
      </main>
    );
  }

  if (isError || !destination) {
    return (
      <main className="destination-detail-page">
        <section className="destination-detail-state">
          <p className="eyebrow">Destination</p>

          <h1>Destination unavailable</h1>

          <p>
            We couldn't load this destination. It may no longer
            be available or there may be a connection problem.
          </p>

          <div className="destination-detail-state-actions">
            <button
              type="button"
              className="primary-action"
              onClick={() => void refetch()}
            >
              Try again
            </button>

            <Link
              className="secondary-action"
              to="/destinations"
            >
              Back to destinations
            </Link>
          </div>
        </section>
      </main>
    );
  }

  const imageUrl = getCloudinaryImageUrl(
    destination.image_url,
    {
      width: 1600,
      height: 900,
    },
  );

  return (
    <main className="destination-detail-page">
      <div className="destination-detail-container">
        <Link
          className="destination-back-link"
          to="/destinations"
        >
          ← Back to destinations
        </Link>

        <section className="destination-detail-hero">
          <div className="destination-detail-image">
            {imageUrl ? (
              <img
                src={imageUrl}
                alt={destination.name}
              />
            ) : (
              <div
                className="destination-detail-image-fallback"
                aria-hidden="true"
              >
                <span>
                  {formatCategory(destination.category)}
                </span>
              </div>
            )}
          </div>

          <div className="destination-detail-intro">
            <p className="eyebrow">
              {formatCategory(destination.category)}
            </p>

            <h1>{destination.name}</h1>

            <p className="destination-detail-location">
              {formatLocation(destination)}
            </p>

            {destination.description && (
              <p className="destination-detail-description">
                {destination.description}
              </p>
            )}

            <div className="destination-detail-actions">
              <Link
                className="primary-action"
                to={`/trips/new?destination=${destination.id}`}
              >
                Add to trip
              </Link>

              <span className="destination-detail-popularity">
                {Math.round(destination.popularity_score)} popularity
              </span>
            </div>
          </div>
        </section>

        <section
          className="destination-detail-grid"
          aria-label="Destination information"
        >
          <article className="destination-info-card">
            <p className="detail-label">VISIT TIME</p>

            <h2>
              {destination.average_visit_duration_minutes !== null
                ? `${destination.average_visit_duration_minutes} min`
                : "Not specified"}
            </h2>
          </article>

          <article className="destination-info-card">
            <p className="detail-label">ENTRY FEE</p>

            <h2>{formatFee(destination)}</h2>
          </article>

          <article className="destination-info-card">
            <p className="detail-label">ACCESSIBILITY</p>

            <h2>
              {destination.accessibility
                ? formatCategory(destination.accessibility)
                : "Not specified"}
            </h2>
          </article>
        </section>

        <section className="destination-detail-sections">
          <article className="destination-information-section">
            <div className="destination-section-heading">
              <p className="detail-label">PLAN YOUR VISIT</p>

              <h2>Good to know</h2>
            </div>

            <div className="destination-information-list">
              <div>
                <span>Opening hours</span>

                <strong>
                  {destination.opening_hours || "Not specified"}
                </strong>
              </div>

              <div>
                <span>Address</span>

                <strong>
                  {[
                    destination.address_line1,
                    destination.address_line2,
                    destination.city,
                    destination.state_province,
                    destination.postal_code,
                  ]
                    .filter(Boolean)
                    .join(", ") || "Address unavailable"}
                </strong>
              </div>

              <div>
                <span>Accessibility notes</span>

                <strong>
                  {destination.accessibility_notes ||
                    "No additional accessibility information."}
                </strong>
              </div>
            </div>
          </article>

          {(destination.website_url ||
            destination.phone_number ||
            destination.email) && (
            <article className="destination-information-section">
              <div className="destination-section-heading">
                <p className="detail-label">CONTACT</p>

                <h2>Useful links</h2>
              </div>

              <div className="destination-contact-list">
                {destination.website_url && (
                  <a
                    href={destination.website_url}
                    target="_blank"
                    rel="noreferrer"
                  >
                    Visit website
                    <span aria-hidden="true">↗</span>
                  </a>
                )}

                {destination.phone_number && (
                  <a
                    href={`tel:${destination.phone_number}`}
                  >
                    {destination.phone_number}
                  </a>
                )}

                {destination.email && (
                  <a
                    href={`mailto:${destination.email}`}
                  >
                    {destination.email}
                  </a>
                )}
              </div>
            </article>
          )}
        </section>
      </div>
    </main>
  );
}