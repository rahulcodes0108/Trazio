import { useMemo, useState } from "react";
import { Link } from "react-router-dom";

import { useDestinations } from "../../hooks/useDestinations";
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

function getPopularityLabel(score: number): string {
  if (score >= 80) return "Highly popular";
  if (score >= 60) return "Popular";
  if (score >= 40) return "Well known";
  return "Discover";
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
      height: 450,
    },
  );

  return (
    <article className="destination-card">
      <div className="destination-card-visual">
        {imageUrl ? (
          <img
            src={imageUrl}
            alt={destination.name}
            loading="lazy"
          />
        ) : (
          <div
            className="destination-card-image-fallback"
            aria-hidden="true"
          >
            <span>{formatCategory(destination.category)}</span>
          </div>
        )}
      </div>

      <div className="destination-card-content">
        <div className="destination-card-heading">
          <div>
            <p className="destination-category">
              {formatCategory(destination.category)}
            </p>

            <h2>{destination.name}</h2>
          </div>

          <span
            className="destination-popularity"
            aria-label={`Popularity score ${Math.round(
              destination.popularity_score,
            )}`}
          >
            {Math.round(destination.popularity_score)}
          </span>
        </div>

        <p className="destination-location">
          {formatLocation(destination)}
        </p>

        {destination.description && (
          <p className="destination-description">
            {destination.description}
          </p>
        )}

        <div className="destination-card-footer">
          <span>
            {getPopularityLabel(destination.popularity_score)}
          </span>

          {destination.average_visit_duration_minutes !== null && (
            <span>
              {destination.average_visit_duration_minutes} min
            </span>
          )}
        </div>

        <Link
          className="destination-view-link"
          to={`/destinations/${destination.slug}`}
        >
          View details
          <span aria-hidden="true">→</span>
        </Link>
      </div>
    </article>
  );
}

export default function DestinationsPage() {
  const {
    data,
    isLoading,
    isError,
    refetch,
  } = useDestinations(0, 100);

  const [search, setSearch] = useState("");
  const [selectedCategory, setSelectedCategory] =
    useState("all");

  const destinations = useMemo(
    () => data?.destinations ?? [],
    [data],
  );

  const categories = useMemo(() => {
    return Array.from(
      new Set(
        destinations
          .map((destination) => destination.category)
          .filter(Boolean),
      ),
    ).sort((a, b) => a.localeCompare(b));
  }, [destinations]);

  const filteredDestinations = useMemo(() => {
    const normalizedSearch = search.trim().toLowerCase();

    return destinations.filter((destination) => {
      const matchesCategory =
        selectedCategory === "all" ||
        destination.category === selectedCategory;

      if (!matchesCategory) {
        return false;
      }

      if (!normalizedSearch) {
        return true;
      }

      const searchableText = [
        destination.name,
        destination.description,
        destination.category,
        destination.city,
        destination.state_province,
        destination.address_line1,
      ]
        .filter(Boolean)
        .join(" ")
        .toLowerCase();

      return searchableText.includes(normalizedSearch);
    });
  }, [
    destinations,
    search,
    selectedCategory,
  ]);

  const hasActiveFilters =
    search.trim().length > 0 ||
    selectedCategory !== "all";

  return (
    <main className="destinations-page">
      <section className="destinations-hero">
        <div>
          <p className="eyebrow">Explore Chennai</p>

          <h1>
            Find places worth adding to your journey.
          </h1>

          <p className="destinations-subtitle">
            Discover destinations and explore the places
            that fit your trip.
          </p>
        </div>

        <Link
          className="secondary-action"
          to="/trips"
        >
          My trips
        </Link>
      </section>

      <section className="destination-discovery-panel">
        <div className="destination-search-row">
          <label
            className="destination-search"
            htmlFor="destination-search"
          >
            <span className="sr-only">
              Search destinations
            </span>

            <span
              className="search-icon"
              aria-hidden="true"
            >
              ⌕
            </span>

            <input
              id="destination-search"
              type="search"
              value={search}
              onChange={(event) =>
                setSearch(event.target.value)
              }
              placeholder="Search destinations..."
            />
          </label>

          {!isLoading && !isError && (
            <span className="destination-count">
              {hasActiveFilters
                ? `${filteredDestinations.length} of ${
                    data?.count ?? destinations.length
                  }`
                : `${
                    data?.count ?? destinations.length
                  } destinations`}
            </span>
          )}
        </div>

        {!isLoading &&
          !isError &&
          categories.length > 0 && (
            <div
              className="destination-category-list"
              aria-label="Destination categories"
            >
              <button
                type="button"
                className={`category-filter ${
                  selectedCategory === "all"
                    ? "active"
                    : ""
                }`}
                onClick={() =>
                  setSelectedCategory("all")
                }
              >
                All
              </button>

              {categories.map((category) => (
                <button
                  key={category}
                  type="button"
                  className={`category-filter ${
                    selectedCategory === category
                      ? "active"
                      : ""
                  }`}
                  onClick={() =>
                    setSelectedCategory(category)
                  }
                >
                  {formatCategory(category)}
                </button>
              ))}
            </div>
          )}
      </section>

      {isLoading && (
        <section
          className="destination-state"
          aria-live="polite"
        >
          <div
            className="loading-spinner"
            aria-hidden="true"
          />

          <p>Discovering destinations...</p>
        </section>
      )}

      {isError && !isLoading && (
        <section className="destination-state">
          <h2>We couldn't load destinations.</h2>

          <p>
            Check your connection and try again.
          </p>

          <button
            type="button"
            className="primary-action"
            onClick={() => void refetch()}
          >
            Try again
          </button>
        </section>
      )}

      {!isLoading &&
        !isError &&
        filteredDestinations.length === 0 && (
          <section className="destination-state">
            <h2>No destinations found.</h2>

            <p>
              Try a different search term or clear the
              category filter.
            </p>

            <button
              type="button"
              className="secondary-action"
              onClick={() => {
                setSearch("");
                setSelectedCategory("all");
              }}
            >
              Clear filters
            </button>
          </section>
        )}

      {!isLoading &&
        !isError &&
        filteredDestinations.length > 0 && (
          <section
            className="destination-grid"
            aria-label="Destinations"
          >
            {filteredDestinations.map((destination) => (
              <DestinationCard
                key={destination.id}
                destination={destination}
              />
            ))}
          </section>
        )}
    </main>
  );
}