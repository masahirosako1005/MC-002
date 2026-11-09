from typing import Annotated, Literal

from pydantic import BaseModel, ConfigDict, Field, StrictInt, StringConstraints


Season = Literal["spring", "summer", "autumn", "winter"]
Identifier = Annotated[str, StringConstraints(min_length=1, max_length=100, pattern=r"^[a-zA-Z0-9_-]+$")]


class InputModel(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)


class EmptyInput(InputModel):
    pass


class VisitInput(InputModel):
    spot_id: Identifier
    code: Annotated[str, StringConstraints(min_length=1, max_length=80)]


class AttemptInput(InputModel):
    game_id: Identifier


class AnswerInput(InputModel):
    values: Annotated[list[Annotated[StrictInt, Field(ge=0, le=5)]], Field(min_length=3, max_length=3)]


class PlanInput(InputModel):
    experience_id: Identifier
    reason: Annotated[str, StringConstraints(min_length=1, max_length=300)]


class RecoveryInput(InputModel):
    recovery_code: Annotated[str, StringConstraints(min_length=1, max_length=128)]


class RecoveryOut(BaseModel):
    recovery_code: str


class SessionOut(BaseModel):
    nickname: str
    csrf_token: str


class SpotOut(BaseModel):
    id: str
    name: str
    area: str
    kind: Literal["gate", "shrine", "coast", "conference"]
    description: str
    walk_minutes: int
    dwell_minutes: int


class ExperienceOut(BaseModel):
    id: str
    spot_id: str
    title: str
    season: Season | Literal["all"]
    description: str
    month_label: str
    duration_minutes: int
    kind: Literal["puzzle", "event", "activity"]


class GameOut(BaseModel):
    id: str
    spot_id: str
    title: str
    season: Season
    difficulty: Literal["beginner", "advanced"]
    description: str
    version: str


class CatalogOut(BaseModel):
    city: str
    season: Season
    spots: list[SpotOut]
    experiences: list[ExperienceOut]
    games: list[GameOut]


class VisitOut(BaseModel):
    id: str
    spot_id: str
    spot_name: str
    visited_at: str


class PuzzleOut(BaseModel):
    title: str
    instruction: str
    labels: list[str]
    max_value: int
    clue: str


class StartedAttemptOut(BaseModel):
    id: str
    game_id: str
    status: str
    hints_used: int
    puzzle: PuzzleOut


class AttemptOut(BaseModel):
    id: str
    game_id: str
    title: str
    season: Season
    status: str
    score: int | None
    hints_used: int
    created_at: str
    completed_at: str | None


class AchievementOut(BaseModel):
    id: str
    title: str
    description: str
    earned_at: str
    season: Season


class PlanOut(BaseModel):
    id: str
    experience_id: str
    title: str
    spot_name: str
    season: Season | Literal["all"]
    month_label: str
    reason: str
    created_at: str


class JournalOut(BaseModel):
    visits: list[VisitOut]
    attempts: list[AttemptOut]
    achievements: list[AchievementOut]
    plans: list[PlanOut]


class CollectionTargetInput(InputModel):
    trophy_id: Identifier | None


class CollectionTargetOut(BaseModel):
    target_id: str | None


class CollectionProgressOut(BaseModel):
    current: int
    target: int
    unit: str


class CollectionStageOut(BaseModel):
    id: str
    title: str
    target: int
    current: int
    completed: bool
    earned_at: str | None


class CollectionActionOut(BaseModel):
    kind: Literal["visit", "puzzle", "season"]
    label: str
    spot_id: str
    season: Season | None
    difficulty: Literal["beginner", "advanced"] | None
    available_from: str | None


class TrophyOut(BaseModel):
    id: str
    set_id: str
    title: str
    description: str
    motif: str
    status: Literal["locked", "progress", "earned"]
    completed: bool
    earned_at: str | None
    progress: CollectionProgressOut
    stages: list[CollectionStageOut]
    missing_conditions: list[str]
    next_action: CollectionActionOut | None


class CollectionSetOut(BaseModel):
    id: str
    title: str
    reward_label: str
    earned: int
    total: int
    completed: bool
    earned_at: str | None


class CollectionSummaryOut(BaseModel):
    earned: int
    total: int
    completed_sets: int


class CollectionOut(BaseModel):
    definition_version: Literal["1"]
    target_id: str | None
    summary: CollectionSummaryOut
    sets: list[CollectionSetOut]
    trophies: list[TrophyOut]


class HintOut(BaseModel):
    hint: str
    hints_used: int


class AnswerOut(BaseModel):
    correct: bool
    score: int | None
    achievement: AchievementOut | None
    message: str


class LeaderboardEntry(BaseModel):
    rank: int
    nickname: str
    score: int


class LeaderboardOut(BaseModel):
    entries: list[LeaderboardEntry]
    game_id: str


class RecommendationOut(BaseModel):
    experience: ExperienceOut
    spot: SpotOut
    total_minutes: int
    travel_minutes: int
    buffer_minutes: int
    reason: str


class RecommendationsOut(BaseModel):
    items: list[RecommendationOut]
    reason: str


class HealthOut(BaseModel):
    status: str


class DeletedOut(BaseModel):
    ok: bool
