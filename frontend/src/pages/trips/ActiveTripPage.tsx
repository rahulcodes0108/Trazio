import {
  useEffect,
  useMemo,
  useRef,
  useState,
} from "react";

import {
  Link,
  useParams,
} from "react-router-dom";

import {
  useItinerary,
  useItineraryStops,
} from "../../hooks/useItineraries";

import { useDestinations } from "../../hooks/useDestinations";

import {
  useLocationTracker,
} from "../../hooks/useLocationTracker";

import {
  evaluateTripContext,
  type LocationContextStatus,
} from "../../lib/location/tripContext";

function formatDuration(
  minutes: number,
): string {
  if (minutes < 60) {
    return `${minutes} min`;
  }

  const hours = Math.floor(
    minutes / 60,
  );

  const remaining =
    minutes % 60;

  if (remaining === 0) {
    return `${hours} hr`;
  }

  return `${hours} hr ${remaining} min`;
}

function formatLocation(
  value: number,
): string {
  return value.toFixed(5);
}

function parseItineraryId(
  value: string | undefined,
): number | null {
  if (!value) {
    return null;
  }

  const parsed =
    Number(value);

  return Number.isInteger(parsed) &&
    parsed > 0
    ? parsed
    : null;
}

interface Coordinates {
  latitude: number;
  longitude: number;
}

function parsePointCoordinates(
  value: string,
): Coordinates | null {
  const match = value.match(
    /POINT\(\s*(-?\d+(?:\.\d+)?)\s+(-?\d+(?:\.\d+)?)\s*\)/i,
  );

  if (!match) {
    return null;
  }

  const longitude =
    Number(match[1]);

  const latitude =
    Number(match[2]);

  if (
    !Number.isFinite(latitude) ||
    !Number.isFinite(longitude)
  ) {
    return null;
  }

  return {
    latitude,
    longitude,
  };
}

function formatContextStatus(
  status: LocationContextStatus,
): string {
  switch (status) {
    case "approaching":
      return "Approaching your current stop";

    case "arrived":
      return "You have arrived";

    case "departed":
      return "You have departed this stop";

    case "missed":
      return "This stop may have been missed";

    case "delayed":
      return "You are running behind schedule";

    case "no_stop":
      return "No active stop";

    default:
      return "Trip context unavailable";
  }
}

function formatDistance(
  meters: number,
): string {
  if (meters < 1_000) {
    return `${Math.round(meters)} m`;
  }

  return `${(
    meters / 1_000
  ).toFixed(1)} km`;
}

export default function ActiveTripPage() {
  const {
    itineraryId,
    tripId,
  } = useParams<{
    itineraryId: string;
    tripId: string;
  }>();

  const parsedItineraryId =
    parseItineraryId(
      itineraryId,
    );

  const parsedTripId =
    parseItineraryId(tripId);

  const itineraryQuery =
    useItinerary(
      parsedItineraryId ?? 0,
    );

  const stopsQuery =
    useItineraryStops(
      parsedItineraryId ?? 0,
    );

  const destinationQuery =
    useDestinations(0, 100);

  const {
    status: locationStatus,
    location,
    error: locationError,
    startTracking,
    stopTracking,
  } = useLocationTracker();

  const destinationById =
    useMemo(() => {
      const destinations =
        destinationQuery.data
          ?.destinations ?? [];

      return new Map(
        destinations.map(
          (destination) => [
            destination.id,
            destination,
          ],
        ),
      );
    }, [
      destinationQuery.data,
    ]);

  const stops =
    stopsQuery.data?.stops ?? [];

  const currentStop =
    stops.length > 0
      ? stops[0]
      : null;

  const nextStop =
    stops.length > 1
      ? stops[1]
      : null;

  const currentDestination =
    currentStop
      ? destinationById.get(
          currentStop.destination_id,
        )
      : null;

  const nextDestination =
    nextStop
      ? destinationById.get(
          nextStop.destination_id,
        )
      : null;

  const previousContextStatusRef =
    useRef<LocationContextStatus>(
      "approaching",
    );

  const [
    contextStatus,
    setContextStatus,
  ] = useState<LocationContextStatus>(
    "no_stop",
  );

  const [
    distanceToCurrentStopMeters,
    setDistanceToCurrentStopMeters,
  ] = useState<number | null>(
    null,
  );

  const [
    distanceToNextStopMeters,
    setDistanceToNextStopMeters,
  ] = useState<number | null>(
    null,
  );

  const currentStopCoordinates =
    useMemo(() => {
      if (!currentDestination) {
        return null;
      }

      return parsePointCoordinates(
        currentDestination.location,
      );
    }, [
      currentDestination,
    ]);

  const nextStopCoordinates =
    useMemo(() => {
      if (!nextDestination) {
        return null;
      }

      return parsePointCoordinates(
        nextDestination.location,
      );
    }, [
      nextDestination,
    ]);

  useEffect(() => {
    if (!currentStop) {
      previousContextStatusRef.current =
        "no_stop";

      setContextStatus("no_stop");
      setDistanceToCurrentStopMeters(
        null,
      );
      setDistanceToNextStopMeters(
        null,
      );

      return;
    }

    /*
     * We cannot evaluate proximity until
     * the destination coordinates are available.
     */
    if (!currentStopCoordinates) {
      setContextStatus("no_stop");
      setDistanceToCurrentStopMeters(
        null,
      );
      setDistanceToNextStopMeters(
        null,
      );

      return;
    }

    /*
     * Context evaluation requires a GPS
     * location. Until then, preserve the
     * current context state.
     */
    if (!location) {
      return;
    }

    const result =
      evaluateTripContext({
        location: {
          latitude:
            location.latitude,
          longitude:
            location.longitude,
        },

        timestamp:
          location.timestamp,

        currentStop: {
          id: currentStop.id,
          destinationId:
            currentStop.destination_id,
          sequence:
            currentStop.sequence,
          coordinates:
            currentStopCoordinates,
          plannedArrival:
            currentStop.planned_arrival,
          plannedDeparture:
            currentStop.planned_departure,
        },

        nextStop:
          nextStop &&
          nextStopCoordinates
            ? {
                id: nextStop.id,
                destinationId:
                  nextStop.destination_id,
                sequence:
                  nextStop.sequence,
                coordinates:
                  nextStopCoordinates,
                plannedArrival:
                  nextStop.planned_arrival,
                plannedDeparture:
                  nextStop.planned_departure,
              }
            : null,

        previousStatus:
          previousContextStatusRef.current,
      });

    setContextStatus(
      result.status,
    );

    setDistanceToCurrentStopMeters(
      result.distanceToCurrentStopMeters,
    );

    setDistanceToNextStopMeters(
      result.distanceToNextStopMeters,
    );

    previousContextStatusRef.current =
      result.status;
  }, [
    location,
    currentStop,
    nextStop,
    currentStopCoordinates,
    nextStopCoordinates,
  ]);

  if (
    !parsedItineraryId ||
    !parsedTripId
  ) {
    return (
      <main className="active-trip-page">
        <section className="active-trip-state">
          <h1>
            Invalid trip
          </h1>

          <p>
            The trip or itinerary
            identifier is invalid.
          </p>

          <Link
            to="/trips"
            className="active-trip-button"
          >
            Back to trips
          </Link>
        </section>
      </main>
    );
  }

  if (
    itineraryQuery.isLoading ||
    stopsQuery.isLoading
  ) {
    return (
      <main className="active-trip-page">
        <section className="active-trip-state">
          <p>
            Loading your active trip...
          </p>
        </section>
      </main>
    );
  }

  if (
    itineraryQuery.isError ||
    stopsQuery.isError ||
    !itineraryQuery.data
  ) {
    return (
      <main className="active-trip-page">
        <section className="active-trip-state">
          <h1>
            Active trip unavailable
          </h1>

          <p>
            We couldn't load this
            itinerary.
          </p>

          <Link
            to={`/trips/${parsedTripId}/itineraries/${parsedItineraryId}`}
            className="active-trip-button"
          >
            Back to itinerary
          </Link>
        </section>
      </main>
    );
  }

  const itinerary =
    itineraryQuery.data;

  return (
    <main className="active-trip-page">
      <header className="active-trip-header">
        <div>
          <p className="active-trip-eyebrow">
            TRAZIO / ACTIVE TRIP
          </p>

          <h1>
            Your trip is underway
          </h1>

          <p className="active-trip-subtitle">
            Itinerary · Version{" "}
            {itinerary.version}
          </p>
        </div>

        <Link
          to={`/trips/${parsedTripId}/itineraries/${parsedItineraryId}`}
          className="active-trip-secondary-button"
        >
          View itinerary
        </Link>
      </header>

      <section className="active-trip-status-card">
        <div>
          <span
            className={`active-trip-status-dot ${
              locationStatus ===
              "tracking"
                ? "is-tracking"
                : ""
            }`}
          />

          <div>
            <strong>
              {locationStatus ===
              "tracking"
                ? "Location tracking active"
                : "Location tracking inactive"}
            </strong>

            <p>
              {locationStatus ===
              "tracking"
                ? "Trazio is receiving your current location for this active trip."
                : "Start location tracking when you're ready to begin."}
            </p>
          </div>
        </div>

        {locationStatus ===
        "tracking" ? (
          <button
            type="button"
            className="active-trip-secondary-button"
            onClick={
              stopTracking
            }
          >
            Stop tracking
          </button>
        ) : (
          <button
            type="button"
            className="active-trip-button"
            onClick={
              startTracking
            }
            disabled={
              locationStatus ===
              "unsupported"
            }
          >
            Start tracking
          </button>
        )}
      </section>

      {locationStatus ===
        "unsupported" && (
        <section className="active-trip-alert">
          <strong>
            Location tracking isn't
            supported
          </strong>

          <p>
            Your browser does not
            provide geolocation
            support.
          </p>
        </section>
      )}

      {locationError && (
        <section className="active-trip-alert">
          <strong>
            Location update
          </strong>

          <p>
            {locationError}
          </p>
        </section>
      )}

      <section className="active-trip-grid">
        <article className="active-trip-card active-trip-card-primary">
          <p className="active-trip-card-label">
            CURRENT STOP
          </p>

          <h2>
            {currentDestination
              ?.name ??
              "No current stop"}
          </h2>

          {currentStop && (
            <>
              <p className="active-trip-card-meta">
                Stop{" "}
                {currentStop.sequence}
                {" · "}
                {formatDuration(
                  currentStop
                    .visit_duration_minutes ??
                    0,
                )}
              </p>

              {currentStop.notes && (
                <p className="active-trip-card-description">
                  {currentStop.notes}
                </p>
              )}
            </>
          )}
        </article>

        <article className="active-trip-card">
          <p className="active-trip-card-label">
            NEXT STOP
          </p>

          <h2>
            {nextDestination
              ?.name ??
              "You're at the final stop"}
          </h2>

          {nextStop && (
            <p className="active-trip-card-meta">
              Stop{" "}
              {nextStop.sequence}
            </p>
          )}
        </article>
      </section>

      <section className="active-trip-context-card">
        <div>
          <p className="active-trip-card-label">
            TRIP CONTEXT
          </p>

          <h2>
            {formatContextStatus(
              contextStatus,
            )}
          </h2>

          <p className="active-trip-card-meta">
            {contextStatus ===
            "arrived"
              ? "Your current location is within the arrival area."
              : contextStatus ===
                  "missed"
                ? "The planned arrival window has passed."
                : contextStatus ===
                    "departed"
                  ? "You have moved beyond the departure area."
                  : contextStatus ===
                      "approaching"
                    ? "Trazio is monitoring your distance to the current stop."
                    : contextStatus ===
                        "no_stop"
                      ? "There is no active destination to evaluate."
                      : "Trazio is evaluating your trip timing."}
          </p>
        </div>

        <div className="active-trip-context-metrics">
          {distanceToCurrentStopMeters !==
            null && (
            <div>
              <span>
                Current stop
              </span>

              <strong>
                {formatDistance(
                  distanceToCurrentStopMeters,
                )}
              </strong>
            </div>
          )}

          {distanceToNextStopMeters !==
            null && (
            <div>
              <span>
                Next stop
              </span>

              <strong>
                {formatDistance(
                  distanceToNextStopMeters,
                )}
              </strong>
            </div>
          )}
        </div>
      </section>

      <section className="active-trip-location-card">
        <div>
          <p className="active-trip-card-label">
            CURRENT LOCATION
          </p>

          {location ? (
            <>
              <h2>
                Location detected
              </h2>

              <p className="active-trip-coordinates">
                {formatLocation(
                  location.latitude,
                )}
                {" , "}
                {formatLocation(
                  location.longitude,
                )}
              </p>

              <p className="active-trip-card-meta">
                Accuracy ±
                {Math.round(
                  location.accuracy,
                )}
                m
              </p>
            </>
          ) : (
            <>
              <h2>
                Waiting for location
              </h2>

              <p className="active-trip-card-meta">
                Start tracking to
                receive your current
                position.
              </p>
            </>
          )}
        </div>

        <div className="active-trip-location-badge">
          {location
            ? "GPS connected"
            : "Waiting for GPS"}
        </div>
      </section>

      <section className="active-trip-progress-card">
        <div className="active-trip-progress-header">
          <div>
            <p className="active-trip-card-label">
              TRIP PROGRESS
            </p>

            <h2>
              {stops.length}{" "}
              {stops.length === 1
                ? "stop"
                : "stops"}
            </h2>
          </div>

          <span>
            {formatDuration(
              itinerary.total_duration_minutes,
            )}
          </span>
        </div>

        <div className="active-trip-progress-track">
          <div
            className="active-trip-progress-fill"
            style={{
              width:
                stops.length > 0
                  ? "8%"
                  : "0%",
            }}
          />
        </div>

        <p className="active-trip-card-meta">
          Active-trip progress is now
          location-aware through the
          trip context engine.
        </p>
      </section>
    </main>
  );
}