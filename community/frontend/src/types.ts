export type User = {
  id: string;
  username: string;
  name: string;
  initials: string;
  color: string;
};
export type Tag = { id: string; label: string };
export type Community = {
  id: string;
  name: string;
  description: string;
  member_count: number;
  role: "owner" | "member";
  cover_key: string;
};
export type Analysis = {
  status: "queued" | "running" | "succeeded" | "failed";
  tags: { id: string; label: string; score: number }[];
  message: string;
  model_version: string | null;
};
export type Media = {
  id: string;
  url: string;
  width: number;
  height: number;
  analysis: Analysis;
};
export type Post = {
  id: string;
  community_id: string;
  author: User;
  body: string;
  tags: string[];
  media: Media[];
  status: "draft" | "published";
  created_at: string;
  place_label: string;
  taken_on: string | null;
  can_edit: boolean;
};
export type Grant = {
  community_id: string;
  use_for_matching: boolean;
  display_in_matches: boolean;
  participate: boolean;
};
export type Preferences = {
  tags: string[];
  learn_from_posts: boolean;
  grants: Grant[];
  evidence: { tag_id: string; post_id: string }[];
};
export type Trip = {
  id: string;
  title: string;
  area: string;
  description: string;
  tags: string[];
  duration: "day" | "overnight";
  budget: number;
  season_label: string;
  cover_key: string;
  source_note: string;
};
export type Participant = {
  id: string;
  name: string;
  initials: string;
  color: string;
  common_tags: string[];
  response: "pending" | "accepted" | "unavailable";
};
export type Proposal = {
  id: string;
  community_id: string;
  purpose: string;
  trip: Trip;
  participants: Participant[];
  my_response: "pending" | "accepted" | "declined";
  status: "pending" | "formed" | "invalidated";
  version: number;
  group_id: string | null;
  reason: string;
  created_at: string;
};
export type Contribution = {
  user_id: string;
  name: string;
  role: "none" | "research" | "schedule" | "food" | "photos";
  note: string;
};
export type Group = {
  id: string;
  community_id: string;
  purpose: string;
  trip: Trip;
  members: User[];
  contributions: Contribution[];
  plan: {
    date: string | null;
    meeting_point: string;
    notes: string;
    version: number;
  };
  created_at: string;
};
export type Bootstrap = {
  accounts: Omit<User, "id">[];
  tags: Tag[];
  model: { status: "ready" | "unavailable"; name: string };
};
