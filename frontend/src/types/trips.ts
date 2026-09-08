export type BudgetLevel =
  | "economy"
  | "mid_range"
  | "luxury"
  | "custom";

export type TransportMode =
  | "walking"
  | "driving"
  | "public_transport"
  | "bicycling"
  | "flight"
  | "mixed";

export type TripStatus =
  | "draft"
  | "planning"
  | "confirmed"
  | "in_progress"
  | "completed"
  | "cancelled";

export interface Trip {
  id: number;
  user_id: number;

  title: string;
  description: string | null;

  start_location: string;
  start_date: string;
  start_time: string | null;

  end_date: string | null;
  end_time: string | null;

  available_duration_minutes: number | null;

  budget_level: BudgetLevel;
  budget_amount: number | null;
  budget_currency: string | null;

  transport_mode: TransportMode;

  preferences: Record<string, unknown> | null;

  status: TripStatus;

  is_public: boolean;
  share_token: string | null;

  created_at: string;
  updated_at: string;
}

export interface TripListResponse {
  trips: Trip[];
  count: number;
}

export interface TripCreateRequest {
  title: string;
  description?: string | null;

  start_location: string;
  start_date: string;
  start_time?: string | null;

  end_date?: string | null;
  end_time?: string | null;

  available_duration_minutes?: number | null;

  budget_level?: BudgetLevel;
  budget_amount?: number | null;
  budget_currency?: string | null;

  transport_mode?: TransportMode;

  preferences?: Record<string, unknown> | null;

  status?: TripStatus;

  is_public?: boolean;
  share_token?: string | null;
}

export type TripUpdateRequest = Partial<TripCreateRequest>;