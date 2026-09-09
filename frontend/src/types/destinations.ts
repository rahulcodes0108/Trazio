export type DestinationCategory = string;

export type AccessibilityLevel = string;

export interface Destination {
  id: number;
  name: string;
  slug: string;
  description: string | null;
  image_url: string | null;
  category: DestinationCategory;
  location: string;

  address_line1: string | null;
  address_line2: string | null;
  city: string | null;
  state_province: string | null;
  postal_code: string | null;
  country: string | null;

  opening_hours: string | null;

  entry_fee: number | null;
  entry_fee_currency: string | null;

  average_visit_duration_minutes: number | null;

  accessibility: AccessibilityLevel;
  accessibility_notes: string | null;

  popularity_score: number;
  is_active: boolean;

  website_url: string | null;
  phone_number: string | null;
  email: string | null;

  created_at: string;
  updated_at: string;
}

export interface DestinationListResponse {
  destinations: Destination[];
  count: number;
}