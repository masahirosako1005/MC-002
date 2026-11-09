import type { User } from "./types";

export type Prefecture = { id: string; name: string; latitude: number; longitude: number };
export type JournalCatalog = { prefectures: Prefecture[]; badges: { id: string; title: string; description: string; prefecture_ids: string[] }[]; evidence_note: string };
export type Journey = { id: string; title: string; version: number; created_at: string; visit_count: number };
export type Visit = {
  id: string; journey_id: string | null; prefecture_id: string; prefecture_name: string;
  visited_on: string; place_label: string; latitude: number | null; longitude: number | null;
  media_id: string | null; media_url: string | null; source: "manual" | "exif";
  visibility: "private" | "community"; community_id: string | null; confirmed: boolean;
  version: number; created_at: string; updated_at: string; evidence_label: string;
};
export type BadgeProgress = { id: string; title: string; description: string; prefecture_ids: string[]; visited_prefecture_ids: string[]; remaining_prefecture_ids: string[]; achieved_count: number; total_count: number; earned: boolean };
export type JournalProfile = { user: User; is_owner: boolean; share_achievements: boolean; version: number; visited_prefectures: Prefecture[]; badges: BadgeProgress[]; shared_visits: Visit[]; evidence_note: string };
export type JournalPhoto = { id: string; url: string; width: number; height: number; location_candidate: { latitude: number; longitude: number } | null };
