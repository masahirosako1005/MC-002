import type { ProviderPlan } from "./marketplace-types";

export const RANK_NAMES = [
  "新客",
  "行者",
  "山伏",
  "先達",
  "大先達",
  "正大先達",
  "前鬼・後鬼",
  "別当",
  "大僧正",
  "勧進元",
] as const;
export type RankStatus = {
  policy_version: "R2";
  rank: number;
  name: string;
  lifetime_points: number;
  recent_points: number;
  lifetime_rank: number;
  guaranteed_rank: number;
  maintenance_points: number | null;
  next_rank: number | null;
  next_rank_points: number | null;
  next_lifetime_points_needed: number;
  next_recent_points_needed: number;
  next_demotion_at: string | null;
  evaluated_at: string;
};

export type Route = {
  id: string;
  origin: string;
  destination: string;
  mode: string;
  one_way_km: number | null;
  one_way_minutes: number | null;
  distance_note: string;
  source_url: string;
  time_source_url?: string;
  checked_on: string;
  zone: "target" | "nearby" | "outside" | "unknown";
};
export type DaytripCatalog = {
  routes: Route[];
  rules: {
    version: string;
    base_points: number;
    distance_cap_km: number;
    leader_points: number;
    rank_thresholds: number[];
    rank_names: string[];
    rank_policy_version: "R2";
    rank_window_days: number;
    rank_lifetime_floor_max: number;
  };
  plans: { plan_id: string; provider_id: string; route_id: string }[];
};
export type Outing = {
  id: string;
  circle_id: string;
  title: string;
  route: Route;
  starts_at: string;
  ends_at: string;
  status: "scheduled" | "reporting" | "confirmed" | "cancelled";
  version: number;
  leader_id: string;
  leader_accepted: boolean;
  plan_id: string | null;
  provider_id: string | null;
  can_manage: boolean;
  is_provider: boolean;
  created_at: string;
  participants: {
    user_id: string;
    name: string;
    accepted: boolean;
    claimed: boolean;
    full_route: boolean;
    confirmed_by: string | null;
    provider_verified: boolean;
    points: number;
    revoked: boolean;
  }[];
};
export type Benefit = {
  id: string;
  provider_id: string;
  plan_id: string;
  title: string;
  min_rank: number;
  rank_policy_version: "R2";
  original_rank_policy: "D1" | "R2";
  discount_type: "amount" | "percent";
  discount_value: number;
  max_discount_yen: number;
  max_redemptions: number;
  starts_on: string;
  ends_on: string;
  status: string;
  version: number;
  funding: "provider";
  combinable: false;
};
export type Redemption = {
  id: string;
  benefit_id: string;
  outing_id: string;
  user_id: string;
  provider_id: string;
  status: "reserved" | "redeemed" | "cancelled";
  version: number;
  original_yen: number;
  discount_yen: number;
  total_yen: number;
  adjustment_required: boolean;
  created_at: string;
};
export type DaytripMe = {
  points: number;
  eligible_points: number;
  rank: number;
  eligible_rank: number;
  rank_status: RankStatus;
  eligible_rank_status: RankStatus;
  next_rank_points: number | null;
  completed_count: number;
  leader_count: number;
  ledger: {
    id: string;
    outing_id: string;
    kind: string;
    points: number;
    eligible_points: number;
    reason: string;
    created_at: string;
  }[];
  benefits: Benefit[];
  redemptions: Redemption[];
};
export type DaytripProviderData = {
  plans: ProviderPlan[];
  links: { plan_id: string; route_id: string }[];
  outings: Outing[];
  benefits: Benefit[];
  redemptions: Redemption[];
};
