export type BudgetBasis = "per_person" | "party_total";
export type BudgetScope = "plan_only" | "whole_trip";
export type Requirements = {
  planned_people: number;
  nights: number;
  budget_yen: number | null;
  budget_basis: BudgetBasis | null;
  budget_scope: BudgetScope | null;
  date_start: string | null;
  interests: string[];
  departure_label: string;
  version: number;
};
export type SharedConditions = Pick<
  Requirements,
  | "planned_people"
  | "nights"
  | "budget_yen"
  | "budget_basis"
  | "budget_scope"
  | "date_start"
>;
export type Provider = {
  id: string;
  name: string;
  description?: string;
  area: string;
};
export type Capabilities = { providers: Provider[] };
export type ItineraryItem = {
  day: number;
  period: "morning" | "afternoon" | "evening";
  place: string;
  description: string;
  travel_minutes: number | null;
};
export type ProviderPlan = {
  id: string;
  provider: Provider;
  title: string;
  summary: string;
  area: string;
  min_people: number;
  max_people: number;
  nights: number;
  price_yen: number;
  price_basis: BudgetBasis;
  price_scope: BudgetScope;
  price_note: string;
  tags: string[];
  itinerary: ItineraryItem[];
  status: "draft" | "published" | "archived";
  version: number;
  source_note: string;
};
export type Party = {
  id: string;
  community_id: string;
  representative_id: string;
  title: string;
  status: "open" | "closed";
  active_account_count: number;
  requirements: Requirements | null;
  can_manage: boolean;
  consultation_id: string | null;
};
export type MarketMessage = {
  id: string;
  author_name: string;
  body: string;
  created_at: string;
};
export type ConditionDraft = {
  id: string;
  candidates: {
    message_id: string;
    candidates: {
      planned_people?: number[];
      nights?: number[];
      budget_yen?: number[];
    };
    needs_confirmation: true;
  }[];
  warning: string;
  status: "needs_confirmation";
};
export type Match = {
  eligible: boolean;
  match_status: "excluded" | "needs_confirmation";
  reasons: string[];
  excluded_reasons: string[];
  unknowns: string[];
  common_tags: string[];
  estimated_total_yen: number;
};
export type Recommendation = Match & { plan: ProviderPlan };
export type RecommendationRun = {
  id: string;
  requirements_version: number;
  items: Recommendation[];
};
export type SelectionPreview = {
  plan: ProviderPlan;
  shared_conditions: SharedConditions;
  match: Match;
  notice: string;
};
export type Consultation = {
  id: string;
  status: "open" | "closed";
  version: number;
  selection: {
    plan: ProviderPlan;
    shared_conditions: SharedConditions;
    share_note: string;
    requirements_version: number;
    unknowns: string[];
  };
  can_close: boolean;
  created_at: string;
};
