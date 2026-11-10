export type OmikujiReward = {
  id: string;
  amount_yen: number;
  status: "available" | "redeemed" | "expired";
  expires_at: string;
  redeemed_at: string | null;
};
export type OmikujiDraw = {
  id: string;
  provider_id: string;
  provider_name: string;
  month: string;
  amount_yen: number;
  rank_level: number;
  created_at: string;
  reward: OmikujiReward | null;
};
export type OmikujiData = {
  month: string;
  can_draw: boolean;
  rank: { level: number; name: string };
  personal_rank: { level: number; name: string };
  odds: { amount_yen: number; probability_percent: number }[];
  draws: OmikujiDraw[];
  terms: string[];
};
