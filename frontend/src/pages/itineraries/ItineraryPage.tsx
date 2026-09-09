import { useMemo, useState } from "react";
import {
  Link,
  useNavigate,
  useParams,
} from "react-router-dom";
import axios from "axios";

import {
  useItinerary,
  useItineraryStops,
  useReplanItinerary,
} from "../../hooks/useItineraries";
import { useDestinations } from "../../hooks/useDestinations";
import ItineraryMap from "../../components/maps/ItineraryMap";

function formatDuration(minutes: number | null): string {
  if (minutes === null) {
    return "Not specified";
  }

  if (minutes === 0) {
    return "0 min";
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

function formatTime(value: string | null): string {
  if (!value) {
    return "Not scheduled";
  }

  const date = new Date(value);

  if (Number.isNaN(date.getTime())) {
    return value;
  }

  return new Intl.DateTimeFormat(undefined, {
    hour: "numeric",
    minute: "2-digit",
  }).format(date);
}

function formatStatus(status: string): string {
  return status.replace(/_/g, " ");
}

function formatTravelMode(mode: string | null): string {
  if (!mode) {
    return "Not specified";
  }

  return mode.replace(/_/g, " ");
}

function formatDistance(distance: number | null): string {
  if (distance === null) {
    return "Not available";
  }

  return `${distance.toFixed(1)} km`;
}

function formatCost(
  amount: number | null,
  currency: string | null,
): string {
  if (amount === null) {
    return "Not available";
  }

  return currency
    ? `${currency} ${amount}`
    : `${amount}`;
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

  return "Unable to load this itinerary.";
}

function parsePointCoordinates(
  location: string,
): [number, number] | null {
  const match = location.match(
    /^POINT\(\s*(-?\d+(?:\.\d+)?)\s+(-?\d+(?:\.\d+)?)\s*\)$/i,
  );

  if (!match) {
    return null;
  }

  const longitude = Number(match[1]);
  const latitude = Number(match[2]);

  if (
    !Number.isFinite(longitude) ||
    !Number.isFinite(latitude)
  ) {
    return null;
  }

  if (
    longitude < -180 ||
    longitude > 180 ||
    latitude < -90 ||
    latitude > 90
  ) {
    return null;
  }

  return [longitude, latitude];
}

export default function ItineraryPage() {
  const { itineraryId } = useParams();
  const navigate = useNavigate();

  const [selectedStopId, setSelectedStopId] =
    useState<number | null>(null);

  const [
    unavailableDestinationIds,
    setUnavailableDestinationIds,
  ] = useState<number[]>([]);

  const [replanReason, setReplanReason] =
    useState("");

  const [showReplanPanel, setShowReplanPanel] =
    useState(false);

  const parsedItineraryId = Number(itineraryId);

  const validItineraryId =
    Number.isFinite(parsedItineraryId) &&
    parsedItineraryId > 0;

  const {
    data: itinerary,
    isLoading: isItineraryLoading,
    isError: isItineraryError,
    error: itineraryError,
    refetch: refetchItinerary,
  } = useItinerary(
    validItineraryId
      ? parsedItineraryId
      : 0,
  );

  const {
    data: stopData,
    isLoading: areStopsLoading,
    isError: areStopsError,
    error: stopsError,
    refetch: refetchStops,
  } = useItineraryStops(
    validItineraryId
      ? parsedItineraryId
      : 0,
  );

  const {
    data: destinationData,
    isLoading: areDestinationsLoading,
    isError: areDestinationsError,
  } = useDestinations(0, 100);

  const replanMutation =
    useReplanItinerary(
      validItineraryId
        ? parsedItineraryId
        : 0,
    );

  const destinationsById = useMemo(
    () =>
      new Map(
        (
          destinationData?.destinations ?? []
        ).map((destination) => [
          destination.id,
          destination,
        ]),
      ),
    [destinationData],
  );

  if (!validItineraryId) {
    return (
      <main className="itinerary-page">
        <div className="itinerary-container">
          <div className="state-card">
            <h2>Invalid itinerary</h2>

            <p>
              The itinerary you're looking for
              doesn't have a valid ID.
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

  if (isItineraryLoading) {
    return (
      <main className="itinerary-page">
        <div className="itinerary-container">
          <p className="page-eyebrow">
            ITINERARY
          </p>

          <h1>
            Loading itinerary...
          </h1>
        </div>
      </main>
    );
  }

  if (
    isItineraryError ||
    !itinerary
  ) {
    return (
      <main className="itinerary-page">
        <div className="itinerary-container">
          <div className="state-card">
            <h2>
              Itinerary unavailable
            </h2>

            <p>
              {getErrorMessage(
                itineraryError,
              )}
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
                onClick={() =>
                  void refetchItinerary()
                }
              >
                Try again
              </button>
            </div>
          </div>
        </div>
      </main>
    );
  }

  const stops = [
    ...(stopData?.stops ?? []),
  ].sort(
    (a, b) =>
      a.sequence - b.sequence,
  );

  const mapStops = stops.flatMap(
    (stop) => {
      const destination =
        destinationsById.get(
          stop.destination_id,
        );

      if (!destination) {
        return [];
      }

      const coordinates =
        parsePointCoordinates(
          destination.location,
        );

      if (!coordinates) {
        return [];
      }

      return [
        {
          id: stop.id,
          sequence: stop.sequence,
          name: destination.name,
          coordinates,
        },
      ];
    },
  );

  const toggleUnavailableDestination = (
    destinationId: number,
  ) => {
    setUnavailableDestinationIds(
      (current) =>
        current.includes(destinationId)
          ? current.filter(
              (id) =>
                id !== destinationId,
            )
          : [
              ...current,
              destinationId,
            ],
    );
  };

  const handleOpenReplan = () => {
    replanMutation.reset();
    setShowReplanPanel(true);
  };

  const handleCancelReplan = () => {
    if (replanMutation.isPending) {
      return;
    }

    setShowReplanPanel(false);
    setUnavailableDestinationIds([]);
    setReplanReason("");
    replanMutation.reset();
  };

  const handleReplan = async () => {
    if (
      unavailableDestinationIds.length ===
      0
    ) {
      return;
    }

    try {
      const newItinerary =
        await replanMutation.mutateAsync({
          unavailable_destination_ids:
            unavailableDestinationIds,
          reason:
            replanReason.trim() ||
            null,
        });

      setUnavailableDestinationIds([]);
      setReplanReason("");
      setShowReplanPanel(false);

      navigate(
        `/itineraries/${newItinerary.id}`,
      );
    } catch {
      /*
       * The mutation error is rendered
       * inside the replan panel.
       */
    }
  };

  return (
    <main className="itinerary-page">
      <div className="itinerary-container">
        <Link
          to={`/trips/${itinerary.trip_id}`}
          className="back-link"
        >
          ← Back to trip
        </Link>

        <header className="itinerary-header">
          <div>
            <p className="page-eyebrow">
              YOUR TRAZIO PLAN
            </p>

            <h1>
              Itinerary · Version{" "}
              {itinerary.version}
            </h1>

            <p className="page-muted">
              Your optimized travel plan.
            </p>
          </div>

          <span
            className={`trip-status status-${itinerary.status}`}
          >
            {formatStatus(
              itinerary.status,
            )}
          </span>
        </header>

        <section className="itinerary-overview">
          <article>
            <span>STOPS</span>

            <strong>
              {itinerary.stop_count}
            </strong>
          </article>

          <article>
            <span>TOTAL TIME</span>

            <strong>
              {formatDuration(
                itinerary.total_duration_minutes,
              )}
            </strong>
          </article>

          <article>
            <span>TRAVEL TIME</span>

            <strong>
              {formatDuration(
                itinerary.estimated_travel_duration_minutes,
              )}
            </strong>
          </article>

          <article>
            <span>ESTIMATED COST</span>

            <strong>
              {formatCost(
                itinerary.estimated_cost,
                itinerary.estimated_cost_currency,
              )}
            </strong>
          </article>
        </section>

        {itinerary.notes && (
          <section className="itinerary-notes">
            <p className="detail-label">
              PLANNING NOTES
            </p>

            <p>
              {itinerary.notes}
            </p>
          </section>
        )}

        <section className="itinerary-replan-card">
          <div className="itinerary-replan-header">
            <div>
              <span className="itinerary-section-eyebrow">
                DYNAMIC PLANNING
              </span>

              <h2>
                Need to change your itinerary?
              </h2>

              <p>
                Mark a destination as
                unavailable and Trazio will
                create a new optimized version
                without changing this itinerary.
              </p>
            </div>

            {!showReplanPanel && (
              <button
                type="button"
                className="itinerary-secondary-button"
                onClick={
                  handleOpenReplan
                }
              >
                Replan trip
              </button>
            )}
          </div>

          {showReplanPanel && (
            <div className="itinerary-replan-body">
              <div className="itinerary-replan-warning">
                <strong>
                  Which destinations are
                  unavailable?
                </strong>

                <span>
                  Select one or more stops
                  that can no longer be
                  visited.
                </span>
              </div>

              <div className="itinerary-replan-stops">
                {stops.map((stop) => {
                  const destination =
                    destinationsById.get(
                      stop.destination_id,
                    );

                  const selected =
                    unavailableDestinationIds.includes(
                      stop.destination_id,
                    );

                  return (
                    <label
                      key={stop.id}
                      className={`itinerary-replan-stop ${
                        selected
                          ? "itinerary-replan-stop-selected"
                          : ""
                      }`}
                    >
                      <input
                        type="checkbox"
                        checked={selected}
                        onChange={() =>
                          toggleUnavailableDestination(
                            stop.destination_id,
                          )
                        }
                        disabled={
                          replanMutation.isPending
                        }
                      />

                      <span className="itinerary-replan-stop-number">
                        {stop.sequence}
                      </span>

                      <span className="itinerary-replan-stop-info">
                        <strong>
                          {destination?.name ??
                            `Destination ${stop.destination_id}`}
                        </strong>

                        <small>
                          {formatTime(
                            stop.planned_arrival,
                          )}

                          {" · "}

                          {formatDuration(
                            stop.visit_duration_minutes,
                          )}
                        </small>
                      </span>
                    </label>
                  );
                })}
              </div>

              <label className="itinerary-replan-reason">
                <span>
                  Reason{" "}
                  <small>
                    (optional)
                  </small>
                </span>

                <textarea
                  value={replanReason}
                  maxLength={500}
                  rows={3}
                  disabled={
                    replanMutation.isPending
                  }
                  onChange={(event) =>
                    setReplanReason(
                      event.target.value,
                    )
                  }
                  placeholder="e.g. Destination closed unexpectedly"
                />

                <small>
                  {replanReason.length}/500
                </small>
              </label>

              {replanMutation.isError && (
                <div
                  className="itinerary-replan-error"
                  role="alert"
                >
                  {getErrorMessage(
                    replanMutation.error,
                  )}
                </div>
              )}

              <div className="itinerary-replan-actions">
                <button
                  type="button"
                  className="itinerary-secondary-button"
                  onClick={
                    handleCancelReplan
                  }
                  disabled={
                    replanMutation.isPending
                  }
                >
                  Cancel
                </button>

                <button
                  type="button"
                  className="itinerary-primary-button"
                  onClick={() =>
                    void handleReplan()
                  }
                  disabled={
                    unavailableDestinationIds.length ===
                      0 ||
                    replanMutation.isPending
                  }
                >
                  {replanMutation.isPending
                    ? "Replanning..."
                    : "Create new itinerary"}
                </button>
              </div>
            </div>
          )}
        </section>

        <section className="itinerary-plan-section">
          <div className="itinerary-section-heading">
            <div>
              <p className="page-eyebrow">
                YOUR DAY
              </p>

              <h2>
                Itinerary timeline
              </h2>
            </div>

            {!areStopsLoading &&
              !areStopsError && (
                <span className="itinerary-stop-count">
                  {stops.length}{" "}
                  {stops.length === 1
                    ? "stop"
                    : "stops"}
                </span>
              )}
          </div>

          {!areStopsLoading &&
            !areStopsError &&
            mapStops.length > 0 && (
              <section className="itinerary-map-section">
                <div className="itinerary-map-heading">
                  <div>
                    <p className="page-eyebrow">
                      ROUTE
                    </p>

                    <h3>
                      Explore your itinerary
                    </h3>
                  </div>

                  <span>
                    {mapStops.length}{" "}
                    {mapStops.length === 1
                      ? "stop"
                      : "stops"}{" "}
                    mapped
                  </span>
                </div>

                <ItineraryMap
                  stops={mapStops}
                  selectedStopId={
                    selectedStopId
                  }
                  onStopSelect={
                    setSelectedStopId
                  }
                />
              </section>
            )}

          {areStopsLoading && (
            <div className="itinerary-state">
              <p>
                Loading itinerary stops...
              </p>
            </div>
          )}

          {areStopsError && (
            <div className="itinerary-state">
              <h3>
                Stops unavailable
              </h3>

              <p>
                {getErrorMessage(
                  stopsError,
                )}
              </p>

              <button
                type="button"
                className="secondary-button"
                onClick={() =>
                  void refetchStops()
                }
              >
                Try again
              </button>
            </div>
          )}

          {!areStopsLoading &&
            !areStopsError &&
            stops.length === 0 && (
              <div className="itinerary-state">
                <h3>
                  No stops yet
                </h3>

                <p>
                  This itinerary doesn't
                  contain any planned stops.
                </p>
              </div>
            )}

          {!areStopsLoading &&
            !areStopsError &&
            stops.length > 0 && (
              <div className="itinerary-timeline">
                {stops.map(
                  (stop, index) => {
                    const destination =
                      destinationsById.get(
                        stop.destination_id,
                      );

                    const isSelected =
                      selectedStopId ===
                      stop.id;

                    return (
                      <article
                        key={stop.id}
                        className={`itinerary-stop ${
                          isSelected
                            ? "itinerary-stop-selected"
                            : ""
                        }`}
                        onClick={() =>
                          setSelectedStopId(
                            stop.id,
                          )
                        }
                      >
                        <div className="timeline-marker-column">
                          <div className="timeline-sequence">
                            {stop.sequence}
                          </div>

                          {index <
                            stops.length -
                              1 && (
                            <div className="timeline-line" />
                          )}
                        </div>

                        <div className="itinerary-stop-content">
                          <div className="itinerary-stop-heading">
                            <div>
                              <p className="itinerary-stop-time">
                                {formatTime(
                                  stop.planned_arrival,
                                )}

                                {stop.planned_departure &&
                                  ` – ${formatTime(
                                    stop.planned_departure,
                                  )}`}
                              </p>

                              <h3>
                                {destination?.name ??
                                  `Destination ${stop.destination_id}`}
                              </h3>

                              {destination && (
                                <p className="itinerary-stop-location">
                                  {destination.location}
                                </p>
                              )}
                            </div>

                            {destination && (
                              <span className="itinerary-category">
                                {destination.category.replace(
                                  /_/g,
                                  " ",
                                )}
                              </span>
                            )}
                          </div>

                          <div className="itinerary-stop-metrics">
                            <div>
                              <span>
                                VISIT
                              </span>

                              <strong>
                                {formatDuration(
                                  stop.visit_duration_minutes,
                                )}
                              </strong>
                            </div>

                            <div>
                              <span>
                                TRAVEL
                              </span>

                              <strong>
                                {formatDuration(
                                  stop.estimated_travel_duration_minutes,
                                )}
                              </strong>
                            </div>

                            <div>
                              <span>
                                DISTANCE
                              </span>

                              <strong>
                                {formatDistance(
                                  stop.estimated_travel_distance_km,
                                )}
                              </strong>
                            </div>

                            <div>
                              <span>
                                MODE
                              </span>

                              <strong>
                                {formatTravelMode(
                                  stop.travel_mode,
                                )}
                              </strong>
                            </div>
                          </div>

                          {stop.selection_reason && (
                            <div className="itinerary-reason">
                              <span>
                                WHY TRAZIO PICKED
                                THIS
                              </span>

                              <p>
                                {
                                  stop.selection_reason
                                }
                              </p>
                            </div>
                          )}

                          {(stop.estimated_cost !==
                            null ||
                            stop.notes) && (
                            <div className="itinerary-stop-footer">
                              {stop.estimated_cost !==
                                null && (
                                <span>
                                  Estimated cost:{" "}
                                  <strong>
                                    {formatCost(
                                      stop.estimated_cost,
                                      stop.estimated_cost_currency,
                                    )}
                                  </strong>
                                </span>
                              )}

                              {stop.notes && (
                                <span>
                                  {stop.notes}
                                </span>
                              )}
                            </div>
                          )}

                          {destination && (
                            <Link
                              to={`/destinations/${destination.slug}`}
                              className="itinerary-destination-link"
                              onClick={(
                                event,
                              ) =>
                                event.stopPropagation()
                              }
                            >
                              View destination →
                            </Link>
                          )}

                          {!destination &&
                            areDestinationsLoading && (
                              <p className="itinerary-destination-loading">
                                Loading destination
                                details...
                              </p>
                            )}

                          {!destination &&
                            areDestinationsError && (
                              <p className="itinerary-destination-loading">
                                Destination details
                                unavailable.
                              </p>
                            )}
                        </div>
                      </article>
                    );
                  },
                )}
              </div>
            )}
        </section>
      </div>
    </main>
  );
}