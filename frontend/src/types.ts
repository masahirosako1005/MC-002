export type Season = 'spring' | 'summer' | 'autumn' | 'winter';
export type Difficulty = 'beginner' | 'advanced';
export type SpotKind = 'gate' | 'shrine' | 'coast' | 'conference';
export interface Spot {
  id: string;
  name: string;
  area: string;
  kind: SpotKind;
  description: string;
  walk_minutes: number;
  dwell_minutes: number;
}
export interface Experience {
  id: string;
  spot_id: string;
  title: string;
  season: Season | 'all';
  description: string;
  month_label: string;
  duration_minutes: number;
  kind: string;
}
export interface Game {
  id: string;
  spot_id: string;
  title: string;
  season: Season;
  difficulty: Difficulty;
  description: string;
  version: string;
}
export interface Catalog {
  city: string;
  season: Season;
  spots: Spot[];
  experiences: Experience[];
  games: Game[];
}
export interface Visit {
  id: string;
  spot_id: string;
  spot_name: string;
  visited_at: string;
}
export interface Attempt {
  id: string;
  game_id: string;
  title: string;
  season: Season;
  status: string;
  score: number | null;
  hints_used: number;
  created_at: string;
  completed_at: string | null;
}
export interface Achievement {
  id: string;
  title: string;
  description: string;
  earned_at: string;
  season: Season;
}
export interface Plan {
  id: string;
  experience_id: string;
  title: string;
  spot_name: string;
  season: Season | 'all';
  month_label: string;
  reason: string;
  created_at: string;
}
export interface Journal {
  visits: Visit[];
  attempts: Attempt[];
  achievements: Achievement[];
  plans: Plan[];
}
export interface Puzzle {
  title: string;
  instruction: string;
  labels: string[];
  max_value: number;
  clue: string;
}
export interface ActiveAttempt {
  id: string;
  game_id: string;
  status: string;
  hints_used: number;
  puzzle: Puzzle;
}
export interface Answer {
  correct: boolean;
  score: number | null;
  achievement: Achievement | null;
  message: string;
}
export interface Recommendation {
  experience: Experience;
  spot: Spot;
  total_minutes: number;
  travel_minutes: number;
  buffer_minutes: number;
  reason: string;
}
export interface Recommendations {
  items: Recommendation[];
  reason: string;
}
export interface Leaderboard {
  entries: { rank: number; nickname: string; score: number }[];
  game_id: string;
}
export const seasons: Season[] = ['spring', 'summer', 'autumn', 'winter'];
export const seasonName: Record<Season | 'all', string> = {
  spring: '春',
  summer: '夏',
  autumn: '秋',
  winter: '冬',
  all: '通年',
};
export const difficultyName: Record<Difficulty, string> = {
  beginner: 'はじめて',
  advanced: 'じっくり',
};
export const emptyJournal: Journal = { visits: [], attempts: [], achievements: [], plans: [] };

export function dateLabel(value: string) {
  const date = new Date(value);
  return Number.isNaN(date.getTime())
    ? '日付未記録'
    : new Intl.DateTimeFormat('ja-JP', {
        year: 'numeric',
        month: 'long',
        day: 'numeric',
        timeZone: 'Asia/Tokyo',
      }).format(date);
}
