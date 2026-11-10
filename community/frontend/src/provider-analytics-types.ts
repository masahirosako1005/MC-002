import type { CityOrigins, ProviderOrigins } from "./ProviderOriginMap";
import type { ResidenceDestination } from "./ResidenceFields";
export type Scope = "self" | "city";
export type WorkspaceTab = "plans" | "consultations" | "circles" | "daytrip";
export type Metric = {
  count: number;
  previous_count: number;
  change_count: number;
  change_percent: number | null;
  unit: string;
  definition: string;
};
export type CityMetric = {
  count: number | null;
  previous_count: number | null;
  change_count: number | null;
  change_percent: number | null;
  unit: string;
  definition: string;
  status: "available" | "insufficient_sample";
  reason: string | null;
};
export type Period = {
  days: number;
  timezone: string;
  start_date: string;
  end_date: string;
  previous_start_date: string;
  previous_end_date: string;
  today_partial: boolean;
};
export type Distribution = {
  label: string;
  status: "available" | "insufficient_sample" | "no_data";
  known_count: number;
  missing_count: number;
  bins: { key: string; label: string; count: number | null }[];
  reason: string | null;
};
export type SelfMetricKey =
  | "consultations"
  | "confirmed_users"
  | "confirmed_visits"
  | "completed_outings";
export type CityMetricKey =
  "visitors" | "returning_visitors" | "visit_days" | "participations";
export type Analytics = {
  provider_id: string;
  generated_at: string;
  period: Period;
  summary: Record<SelfMetricKey, Metric>;
  daily: ({ date: string } & Record<SelfMetricKey, number>)[];
  plans: ({ id: string; title: string; status: "published" } & Record<
    SelfMetricKey,
    number
  >)[];
  conditions: {
    population_unit: string;
    sample_count: number;
    unique_sharers: number;
    consultation_count: number;
    people: Distribution;
    nights: Distribution;
    budget_per_person: Distribution;
  };
  demographics: Record<
    "age" | "gender" | "interests",
    {
      status: "not_collected";
      reason: string;
      known_count: number;
      missing_count: number;
    }
  >;
  notes: string[];
  origins: ProviderOrigins;
};
export type CityAnalytics = {
  scope: "city";
  city: ResidenceDestination;
  generated_at: string;
  period: Period;
  provider_count: number;
  published_plan_count: number;
  summary: Record<CityMetricKey, CityMetric>;
  daily: {
    status: "available" | "insufficient_sample" | "no_data";
    reason: string | null;
    items: ({ date: string } & Record<CityMetricKey, number | null>)[];
  };
  providers: {
    status: "available" | "insufficient_sample" | "no_data";
    reason: string | null;
    items: {
      id: string;
      name: string;
      area: string;
      published_plan_count: number;
      visitors: number | null;
      participations: number | null;
      completed_outings: number | null;
    }[];
  };
  origins: CityOrigins;
  notes: string[];
  privacy_threshold: number;
  trend: {
    status: "available" | "insufficient_sample" | "no_data";
    reason: string | null;
    interval_days: number;
    items: ({ date: string; end_date: string } & Record<
      CityMetricKey,
      number | null
    >)[];
  };
  plan_categories: { id: string; label: string; plan_count: number }[];
};
export type DisplayMetric = {
  key: string;
  label: string;
  short: string;
  value: Metric | CityMetric;
};
export type TrendDay = {
  date: string;
  endDate?: string;
  values: (number | null)[];
};
