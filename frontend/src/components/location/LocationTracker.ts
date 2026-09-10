export interface UserLocation {
  latitude: number;
  longitude: number;
  accuracy: number;
  timestamp: number;
}

export type LocationTrackerStatus =
  | "idle"
  | "tracking"
  | "unsupported"
  | "permission_denied"
  | "error";

export interface LocationTrackerOptions {
  enableHighAccuracy?: boolean;
  maximumAge?: number;
  timeout?: number;
}

export type LocationUpdateHandler = (
  location: UserLocation,
) => void;

export type LocationErrorHandler = (
  error: GeolocationPositionError,
) => void;

const DEFAULT_OPTIONS: PositionOptions = {
  enableHighAccuracy: true,
  maximumAge: 10_000,
  timeout: 15_000,
};

export class LocationTracker {
  private watchId: number | null = null;

  private readonly options: PositionOptions;

  private readonly onLocation: LocationUpdateHandler;

  private readonly onError: LocationErrorHandler;

  constructor(
    onLocation: LocationUpdateHandler,
    onError: LocationErrorHandler,
    options: LocationTrackerOptions = {},
  ) {
    this.onLocation = onLocation;
    this.onError = onError;

    this.options = {
      ...DEFAULT_OPTIONS,
      ...options,
    };
  }

  isSupported(): boolean {
    return (
      typeof navigator !== "undefined" &&
      "geolocation" in navigator
    );
  }

  start(): boolean {
    if (!this.isSupported()) {
      return false;
    }

    if (this.watchId !== null) {
      return true;
    }

    this.watchId =
      navigator.geolocation.watchPosition(
        (position: GeolocationPosition) => {
          this.onLocation({
            latitude:
              position.coords.latitude,
            longitude:
              position.coords.longitude,
            accuracy:
              position.coords.accuracy,
            timestamp:
              position.timestamp,
          });
        },
        (error: GeolocationPositionError) => {
          this.onError(error);
        },
        this.options,
      );

    return true;
  }

  stop(): void {
    if (this.watchId === null) {
      return;
    }

    if (this.isSupported()) {
      navigator.geolocation.clearWatch(
        this.watchId,
      );
    }

    this.watchId = null;
  }

  isTracking(): boolean {
    return this.watchId !== null;
  }
}