import type { User } from "./types";
import type { Provider } from "./marketplace-types";

export type ReflectionAspect = "guidance" | "response" | "experience" | "price";
export type ReflectionSentiment =
  "positive" | "negative" | "mixed" | "excluded";
export type ReflectionValue = {
  aspect_id: ReflectionAspect;
  sentiment: ReflectionSentiment;
};
export const reflectionAspects: { id: ReflectionAspect; label: string }[] = [
  { id: "guidance", label: "案内の分かりやすさ" },
  { id: "response", label: "対応" },
  { id: "experience", label: "体験内容" },
  { id: "price", label: "価格への納得" },
];
export const reflectionSentiments = {
  positive: "肯定的",
  negative: "否定的",
  mixed: "両方の感想",
  excluded: "集計に使わない",
};
export type ReflectionMessage = {
  id: string;
  author: User;
  is_mine: boolean;
  body: string;
  version: number;
  source_version: number;
  created_at: string;
  extraction: {
    status: "waiting" | "auto_included" | "author_corrected" | "excluded";
    reason: string;
    proposed: ReflectionValue[];
    effective: ReflectionValue[];
    can_correct: boolean;
    source_version: number;
  };
};
export type ReflectionSummary = {
  id: string;
  circle_id: string;
  provider: Provider;
  ended_on: string;
  trip_finished: boolean;
  version: number;
  epoch: number;
  participant_set_current: boolean;
  ready_for_analysis: boolean;
  target_count: number;
  usage_confirmed_count: number;
  consented_count: number;
};
export type Reflection = ReflectionSummary & {
  participants: { user: User; used_service: boolean; consented: boolean }[];
  my_state: { used_service: boolean; consented: boolean; version: number };
  messages: ReflectionMessage[];
  method: string;
  usage_notice: string;
  can_manage: boolean;
};
export type ReflectionOptions = {
  items: {
    invitation_id: string;
    provider: Provider;
    plan_title: string;
    earliest_end_on: string;
  }[];
  reflections: ReflectionSummary[];
};
export type PublicExperienceSummary = {
  status: "available" | "insufficient";
  trip_count: number | null;
  minimum_trip_count: number;
  facets: {
    aspect_id: ReflectionAspect;
    label: string;
    status: "positive" | "negative" | "mixed" | "insufficient";
    trip_count: number | null;
    summary: string;
  }[];
  method: string;
  note: string;
  ranking_signal: number;
};
