import type { User } from "./types";
import type { DiscoveryItem } from "./PlanDiscovery";
export type Occurrence = {
  occurrence_date: string;
  occurrence_year: number;
  days_until: number;
  leap_adjusted: boolean;
};
export type OccasionDate = {
  kind: "birthday" | "anniversary";
  name: string;
  month: number;
  day: number;
  repeats_annually: boolean;
  year: number | null;
};
export type OccasionSharing = {
  circle_id: string;
  circle_title: string;
  share_date: boolean;
  suggest: boolean;
};
export type Occasion = OccasionDate & {
  id: string;
  version: number;
  sharing: OccasionSharing[];
  next_occurrence: Occurrence | null;
};
export type OccasionCircle = {
  id: string;
  title: string;
  community_id: string;
};
export type MyOccasions = { items: Occasion[]; circles: OccasionCircle[] };
export type SharedOccasion = OccasionDate & {
  id: string;
  owner: User;
  next_occurrence: Occurrence | null;
  suggestions_enabled: boolean;
};
export type OccasionSuggestion = {
  id: string;
  occasion_id: string;
  owner: User;
  name: string;
  kind: "birthday" | "anniversary";
  occurrence: Occurrence | null;
  circle_id: string;
  occasion_version: number;
  state: "new" | "later" | "dismissed";
  version: number;
  shared: boolean;
  candidates: DiscoveryItem[];
  notice: string;
};
