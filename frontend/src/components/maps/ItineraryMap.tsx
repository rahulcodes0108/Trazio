import { useEffect, useRef } from "react";
import mapboxgl from "mapbox-gl";

import "mapbox-gl/dist/mapbox-gl.css";

export interface ItineraryMapStop {
  id: number;
  sequence: number;
  name: string;
  coordinates: [number, number];
}

interface ItineraryMapProps {
  stops: ItineraryMapStop[];
  selectedStopId: number | null;
  onStopSelect: (stopId: number) => void;
}

interface DirectionsRoute {
  geometry?: {
    type: "LineString";
    coordinates: [number, number][];
  };
}

interface DirectionsResponse {
  code: string;
  routes?: DirectionsRoute[];
}

const MAPBOX_TOKEN =
  import.meta.env.VITE_MAPBOX_PUBLIC_TOKEN;

const ROUTE_SOURCE_ID =
  "trazio-itinerary-route";

const ROUTE_LAYER_ID =
  "trazio-itinerary-route-line";

function createMarkerElement(
  stop: ItineraryMapStop,
  selected: boolean,
): HTMLButtonElement {
  const element =
    document.createElement("button");

  element.type = "button";

  element.className =
    "itinerary-map-marker";

  if (selected) {
    element.classList.add(
      "itinerary-map-marker-selected",
    );
  }

  element.textContent =
    String(stop.sequence);

  element.title = stop.name;

  element.setAttribute(
    "aria-label",
    `Stop ${stop.sequence}: ${stop.name}`,
  );

  return element;
}

export default function ItineraryMap({
  stops,
  selectedStopId,
  onStopSelect,
}: ItineraryMapProps) {
  const containerRef =
    useRef<HTMLDivElement | null>(
      null,
    );

  const mapRef =
    useRef<mapboxgl.Map | null>(
      null,
    );

  const markersRef =
    useRef<Map<number, mapboxgl.Marker>>(
      new Map(),
    );

  const onStopSelectRef =
    useRef(onStopSelect);

  useEffect(() => {
    onStopSelectRef.current =
      onStopSelect;
  }, [onStopSelect]);

  /*
   * Create the Mapbox instance once.
   */
  useEffect(() => {
    if (
      !containerRef.current ||
      !MAPBOX_TOKEN
    ) {
      return;
    }

    mapboxgl.accessToken =
      MAPBOX_TOKEN;

    const map = new mapboxgl.Map({
      container: containerRef.current,
      style:
        "mapbox://styles/mapbox/streets-v12",
      center: [80.2707, 13.0827],
      zoom: 11,
    });

    map.addControl(
      new mapboxgl.NavigationControl(),
      "top-right",
    );

    mapRef.current = map;

    return () => {
      markersRef.current.forEach(
        (marker) => {
          marker.remove();
        },
      );

      markersRef.current.clear();

      map.remove();

      mapRef.current = null;
    };
  }, []);

  /*
   * Render itinerary markers.
   */
  useEffect(() => {
    const map = mapRef.current;

    if (!map) {
      return;
    }

    const renderMarkers = () => {
      markersRef.current.forEach(
        (marker) => {
          marker.remove();
        },
      );

      markersRef.current.clear();

      if (stops.length === 0) {
        return;
      }

      const bounds =
        new mapboxgl.LngLatBounds();

      stops.forEach((stop) => {
        const element =
          createMarkerElement(
            stop,
            stop.id === selectedStopId,
          );

        element.addEventListener(
          "click",
          (event) => {
            event.stopPropagation();

            onStopSelectRef.current(
              stop.id,
            );
          },
        );

        const marker =
          new mapboxgl.Marker({
            element,
          })
            .setLngLat(stop.coordinates)
            .addTo(map);

        markersRef.current.set(
          stop.id,
          marker,
        );

        bounds.extend(
          stop.coordinates,
        );
      });

      if (stops.length === 1) {
        map.flyTo({
          center: stops[0].coordinates,
          zoom: 13,
          duration: 500,
        });
      } else {
        map.fitBounds(bounds, {
          padding: 70,
          maxZoom: 14,
          duration: 500,
        });
      }
    };

    if (map.isStyleLoaded()) {
      renderMarkers();
    } else {
      map.once(
        "load",
        renderMarkers,
      );
    }

    return () => {
      map.off(
        "load",
        renderMarkers,
      );
    };
  }, [stops]);

  /*
   * Highlight selected marker and
   * move the map to it.
   */
  useEffect(() => {
    const map = mapRef.current;

    if (!map) {
      return;
    }

    markersRef.current.forEach(
      (marker, stopId) => {
        const element =
          marker.getElement();

        element.classList.toggle(
          "itinerary-map-marker-selected",
          stopId === selectedStopId,
        );
      },
    );

    if (
      selectedStopId === null
    ) {
      return;
    }

    const selectedStop =
      stops.find(
        (stop) =>
          stop.id ===
          selectedStopId,
      );

    if (!selectedStop) {
      return;
    }

    map.flyTo({
      center:
        selectedStop.coordinates,
      zoom: Math.max(
        map.getZoom(),
        13,
      ),
      duration: 500,
    });
  }, [
    selectedStopId,
    stops,
  ]);

  /*
   * Request the actual Mapbox road
   * route between itinerary stops.
   */
  useEffect(() => {
    const map = mapRef.current;

    if (
      !map ||
      !MAPBOX_TOKEN ||
      stops.length < 2
    ) {
      return;
    }

    let cancelled = false;

    const removeRoute = () => {
      if (
        map.getLayer(
          ROUTE_LAYER_ID,
        )
      ) {
        map.removeLayer(
          ROUTE_LAYER_ID,
        );
      }

      if (
        map.getSource(
          ROUTE_SOURCE_ID,
        )
      ) {
        map.removeSource(
          ROUTE_SOURCE_ID,
        );
      }
    };

    const renderRoute = (
      geometry: {
        type: "LineString";
        coordinates: [
          number,
          number,
        ][];
      },
    ) => {
      if (
        cancelled ||
        !map.isStyleLoaded()
      ) {
        return;
      }

      removeRoute();

      map.addSource(
        ROUTE_SOURCE_ID,
        {
          type: "geojson",
          data: {
            type: "Feature",
            properties: {},
            geometry,
          },
        },
      );

      map.addLayer({
        id: ROUTE_LAYER_ID,
        type: "line",
        source:
          ROUTE_SOURCE_ID,
        layout: {
          "line-join": "round",
          "line-cap": "round",
        },
        paint: {
          "line-color":
            "#102a56",
          "line-width": 5,
          "line-opacity": 0.8,
        },
      });
    };

    const loadRoute =
      async () => {
        const coordinates =
          stops
            .map(
              (stop) =>
                `${stop.coordinates[0]},${stop.coordinates[1]}`,
            )
            .join(";");

        const url =
          `https://api.mapbox.com/directions/v5/` +
          `mapbox/driving/${coordinates}` +
          `?overview=full` +
          `&geometries=geojson` +
          `&access_token=${encodeURIComponent(
            MAPBOX_TOKEN,
          )}`;

        try {
          const response =
            await fetch(url);

          if (!response.ok) {
            throw new Error(
              `Directions request failed: ${response.status}`,
            );
          }

          const data =
            (await response.json()) as DirectionsResponse;

          const geometry =
            data.routes?.[0]
              ?.geometry;

          if (
            cancelled ||
            data.code !== "Ok" ||
            !geometry
          ) {
            return;
          }

          if (
            map.isStyleLoaded()
          ) {
            renderRoute(
              geometry,
            );
          } else {
            map.once(
              "load",
              () => {
                renderRoute(
                  geometry,
                );
              },
            );
          }
        } catch {
          /*
           * Markers remain available even
           * if routing fails.
           */
        }
      };

    void loadRoute();

    return () => {
      cancelled = true;
      removeRoute();
    };
  }, [stops]);

  if (!MAPBOX_TOKEN) {
    return (
      <div className="itinerary-map-state">
        <h3>
          Map unavailable
        </h3>

        <p>
          Add
          {" "}
          VITE_MAPBOX_PUBLIC_TOKEN
          {" "}
          to the frontend
          environment to enable
          the itinerary map.
        </p>
      </div>
    );
  }

  return (
    <div className="itinerary-map-shell">
      <div
        ref={containerRef}
        className="itinerary-map"
        aria-label="Itinerary map"
      />
    </div>
  );
}