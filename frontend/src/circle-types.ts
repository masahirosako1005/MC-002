import type { User } from "./types";
import type {
  ItineraryItem,
  MarketMessage,
  Provider,
  ProviderPlan,
  Requirements,
  SharedConditions,
} from "./marketplace-types";

export type CircleInvitation = {
  id: string;
  circle_id: string;
  circle_title: string;
  invitee: User;
  inviter: User;
  status: string;
  version: number;
  created_at: string;
};
export type ProviderInvitation = {
  id: string;
  circle_id: string;
  provider: Provider;
  inviter_name: string;
  status: string;
  version: number;
  snapshot: {
    plan: ProviderPlan;
    shared_conditions: SharedConditions;
    share_note: string;
    requirements_version: number;
    unknowns: string[];
  };
  consultation_id: string | null;
  created_at: string;
  accepted_at: string | null;
};
export type CircleSummary = {
  tags: string[];
  id: string;
  community_id: string;
  title: string;
  representative_id: string;
  can_manage: boolean;
  status: string;
  version: number;
  mode: string;
  desired_count: number;
  accepted_count: number;
  pending_count: number;
  shortage_count: number;
  requirements: Requirements | null;
  active_provider_invitation: ProviderInvitation | null;
};
export type CircleDetail = CircleSummary & {
  members: User[];
  invitations: CircleInvitation[];
};
export type CircleList = {
  items: CircleSummary[];
  invitations: CircleInvitation[];
  groups: {
    id: string;
    purpose: string;
    community_id: string;
    member_count: number;
    circle_id: string | null;
  }[];
};
export type CircleCandidates = {
  items: { user: User; common_tags: string[] }[];
  desired_count: number;
  available_count: number;
  shortage_count: number;
  method: string;
};
export type AssistantTurn = {
  id: string;
  user_body: string;
  author_name: string;
  reply: string;
  proposed_conditions: Partial<Requirements>;
  missing_fields: string[];
  ambiguities: string[];
  candidates: {
    plan: ProviderPlan;
    reasons: string[];
    unknowns: string[];
    estimated_total_yen: number;
  }[];
  requirements_version: number;
  method: string;
  needs_confirmation: boolean;
  created_at: string;
};
export type CircleProposal = {
  id: string;
  invitation_id: string;
  version: number;
  title: string;
  date_start: string | null;
  itinerary: ItineraryItem[];
  estimated_price_yen: number;
  price_basis: "per_person" | "party_total";
  price_scope: "plan_only" | "whole_trip";
  price_note: string;
  unknowns: string[];
  created_at: string;
  created_by: string;
  confirmations: {
    role: "traveler" | "provider";
    user: User;
    confirmed_at: string;
  }[];
  status: string;
  reservation_status: "not_booked";
};
export type CircleRoom = {
  invitation: ProviderInvitation;
  messages: MarketMessage[];
  proposal: CircleProposal | null;
  can_propose: boolean;
  can_confirm: boolean;
  my_role: "traveler" | "provider";
  reservation_status: "not_booked";
};
