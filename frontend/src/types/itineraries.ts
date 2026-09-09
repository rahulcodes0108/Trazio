export type ItineraryStatus =
  | "draft"
  | "generated"
  | "optimized"
  | "confirmed"
  | "in_progress"
  | "completed"
  | "archived";

export interface Itinerary {
  id: number;
  trip_id: number;
  version: number;
  status: ItineraryStatus;
  notes: string | null;
  total_duration_minutes: number;
  estimated_travel_duration_minutes: number;
  estimated_cost: number;
  estimated_cost_currency: string | null;
  is_optimized: boolean;
  stop_count: number;
  created_at: string;
  updated_at: string;
}

export interface ItineraryListResponse {
  itineraries: Itinerary[];
  count: number;
}

export interface ItineraryStop {
  id: number;
  itinerary_id: number;
  destination_id: number;
  sequence: number;
  planned_arrival: string | null;
  planned_departure: string | null;
  visit_duration_minutes: number | null;
  estimated_travel_duration_minutes: number | null;
  estimated_travel_distance_km: number | null;
  travel_mode: string | null;
  selection_reason: string | null;
  notes: string | null;
  estimated_cost: number | null;
  estimated_cost_currency: string | null;
  created_at: string;
  updated_at: string;
}

export interface ItineraryStopListResponse {
  stops: ItineraryStop[];
  count: number;
}

export interface ReplanRequest {
  unavailable_destination_ids: number[];
  reason?: string | null;
}