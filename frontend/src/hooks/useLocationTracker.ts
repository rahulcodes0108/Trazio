import {
  useCallback,
  useEffect,
  useRef,
  useState,
} from "react";

import {
  LocationTracker,
  type LocationTrackerOptions,
  type UserLocation,
} from "../components/location/LocationTracker";

type LocationStatus =
  | "idle"
  | "tracking"
  | "unsupported"
  | "permission_denied"
  | "error";

interface UseLocationTrackerResult {
  status: LocationStatus;
  location: UserLocation | null;
  error: string | null;
  startTracking: () => void;
  stopTracking: () => void;
}

function getGeolocationErrorMessage(
  error: GeolocationPositionError,
): {
  status:
    | "permission_denied"
    | "error";
  message: string;
} {
  if (
    error.code ===
    GeolocationPositionError.PERMISSION_DENIED
  ) {
    return {
      status: "permission_denied",
      message:
        "Location permission was denied. Allow location access in your browser to track your trip.",
    };
  }

  if (
    error.code ===
    GeolocationPositionError.POSITION_UNAVAILABLE
  ) {
    return {
      status: "error",
      message:
        "Your current location is temporarily unavailable.",
    };
  }

  if (
    error.code ===
    GeolocationPositionError.TIMEOUT
  ) {
    return {
      status: "error",
      message:
        "Location detection timed out. We will keep trying.",
    };
  }

  return {
    status: "error",
    message:
      "Unable to determine your current location.",
  };
}

export function useLocationTracker(
  options?: LocationTrackerOptions,
): UseLocationTrackerResult {
  const [status, setStatus] =
    useState<LocationStatus>("idle");

  const [location, setLocation] =
    useState<UserLocation | null>(
      null,
    );

  const [error, setError] =
    useState<string | null>(null);

  const trackerRef =
    useRef<LocationTracker | null>(
      null,
    );

  useEffect(() => {
    const tracker =
      new LocationTracker(
        (nextLocation: UserLocation) => {
          setLocation(nextLocation);
          setError(null);
          setStatus("tracking");
        },
        (
          trackerError: GeolocationPositionError,
        ) => {
          const result =
            getGeolocationErrorMessage(
              trackerError,
            );

          setStatus(result.status);
          setError(result.message);
        },
        options,
      );

    trackerRef.current = tracker;

    if (!tracker.isSupported()) {
      setStatus("unsupported");
    }

    return () => {
      tracker.stop();
      trackerRef.current = null;
    };
  }, [options]);

  const startTracking =
    useCallback(() => {
      const tracker =
        trackerRef.current;

      if (!tracker) {
        return;
      }

      if (!tracker.isSupported()) {
        setStatus("unsupported");
        setError(
          "Location tracking is not supported by this browser.",
        );
        return;
      }

      setError(null);

      const started =
        tracker.start();

      if (started) {
        setStatus("tracking");
      }
    }, []);

  const stopTracking =
    useCallback(() => {
      const tracker =
        trackerRef.current;

      if (!tracker) {
        return;
      }

      tracker.stop();

      setStatus("idle");
      setError(null);
    }, []);

  return {
    status,
    location,
    error,
    startTracking,
    stopTracking,
  };
}