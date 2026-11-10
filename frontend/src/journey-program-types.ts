export type ProgramStep = {
  id: string;
  order: number;
  title: string;
  purpose: string;
  plan_id: string;
  plan_title: string;
  price_yen: number;
  route_id: string;
};
export type ProgramProgress = {
  step_id: string;
  status:
    "unplanned" | "planned" | "awaiting_confirmation" | "completed" | "invalid";
  outing_id: string | null;
  has_link: boolean;
  reason: string | null;
};
export type ProgramEnrollment = {
  version: number;
  status: "active" | "completed" | "cancelled";
  completed_count: number;
  total_steps: number;
  steps: ProgramProgress[];
};
export type JourneyProgram = {
  available: boolean;
  unavailable_reason: string | null;
  id: string;
  title: string;
  goal: string;
  area: string;
  provider: { id: string; name: string };
  recommended_interval: string;
  price_basis: "per_person";
  price_scope: "plan_only";
  total_price_yen: number;
  price_note: string;
  steps: ProgramStep[];
  enrollment: ProgramEnrollment | null;
};
export type ProgramCatalog = { items: JourneyProgram[]; notice: string };
export type ProgramOuting = {
  id: string;
  title: string;
  starts_at: string;
  ends_at: string;
  plan_id: string;
  status: string;
};
