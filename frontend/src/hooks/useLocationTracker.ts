import {
  useCallback,
  useEffect,
  useRef,
  useState,
} from "react";

import {
  LocationTracker,
  type LocationTrackerStatus,
  type UserLocation,
} from "../components/location/LocationTracker";

export interface LocationTrackerState {
  location: UserLocation | null;
  status: LocationTrackerStatus;
  error: string | null;
}

function getGeolocationErrorMessage(
  error: GeolocationPositionError,
): string {
  switch (error.code) {
    case error.PERMISSION_DENIED:
      return "Location permission was denied.";

    case error.POSITION_UNAVAILABLE:
      return "Your current location is unavailable.";

    case error.TIMEOUT:
      return "Location request timed out.";

    default:
      return "Unable to determine your location.";
  }
}

export function useLocationTracker() {
  const trackerRef =
    useRef<LocationTracker | null>(null);

  const [state, setState] =
    useState<LocationTrackerState>({
      location: null,
      status: "idle",
      error: null,
    });

  useEffect(() => {
    const tracker = new LocationTracker(
      (location) => {
        setState((previous) => ({
          ...previous,
          location,
          status: "tracking",
          error: null,
        }));
      },

      (error) => {
        const message =
          getGeolocationErrorMessage(error);

        const status: LocationTrackerStatus =
          error.code ===
          error.PERMISSION_DENIED
            ? "permission_denied"
            : "error";

        setState((previous) => ({
          ...previous,
          status,
          error: message,
        }));
      },
    );

    trackerRef.current = tracker;

    if (!tracker.isSupported()) {
      setState((previous) => ({
        ...previous,
        status: "unsupported",
        error:
          "Geolocation is not supported by this browser.",
      }));
    }

    return () => {
      tracker.stop();
      trackerRef.current = null;
    };
  }, []);

  const startTracking = useCallback(() => {
    const tracker = trackerRef.current;

    if (!tracker) {
      return;
    }

    if (!tracker.isSupported()) {
      setState((previous) => ({
        ...previous,
        status: "unsupported",
        error:
          "Geolocation is not supported by this browser.",
      }));

      return;
    }

    const started = tracker.start();

    if (started) {
      setState((previous) => ({
        ...previous,
        status: "tracking",
        error: null,
      }));
    }
  }, []);

  const stopTracking = useCallback(() => {
    trackerRef.current?.stop();

    setState((previous) => ({
      ...previous,
      status: "idle",
    }));
  }, []);

  return {
    location: state.location,
    status: state.status,
    error: state.error,
    startTracking,
    stopTracking,
  };
}