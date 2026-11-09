"""Versioned collection rules, derived only from persisted visit/completion evidence.

Keep v1 rule IDs and thresholds stable: changing the current catalog must never
remove an earned keepsake. Preferences are independent of these read-only rules.
"""

from datetime import date, datetime, timedelta
from typing import Any

from .clock import SEASONS, SEASON_NAMES, local_time, season_at


PLACE_NAMES = {
    "watergate": "四季の水門", "sakura": "桜社", "coast": "凪の海辺", "conference": "水都国際会議館",
}
PLACE_TITLES = {"watergate": "水門の鍵", "sakura": "桜社の花守り", "coast": "凪の貝殻", "conference": "水都の招待状"}
SEASON_TITLES = {"spring": "花を運ぶ水路", "summer": "夕涼みの水路", "autumn": "紅葉を映す水路", "winter": "灯りをつなぐ水路"}
TROPHY_IDS = frozenset(
    [f"place-{spot}" for spot in PLACE_NAMES] + [f"season-{season}" for season in SEASONS]
    + ["return-path", "coast-seasons", "conference-detour", "watergate-mastery"]
)
SET_DEFINITIONS = (
    ("places", "まちのしるし", "水都を歩く人"),
    ("seasons", "四季の水路", "四季をつなぐ人"),
    ("journeys", "続く旅", "水都に通う人"),
)


def first_per_key(rows: list[dict], key: str, timestamp: str) -> list[str]:
    """Earliest evidence for each distinct key, in chronological order."""
    earliest: dict[str, str] = {}
    for row in rows:
        value = row[timestamp]
        earliest[row[key]] = min(earliest.get(row[key], value), value)
    return sorted(earliest.values())


def milestones(points: list[str], thresholds: tuple[int, ...]) -> dict[int, str | None]:
    return {threshold: points[threshold - 1] if len(points) >= threshold else None for threshold in thresholds}


def action(kind: str, label: str, spot_id: str, *, season: str | None = None,
           difficulty: str | None = None, available_from: str | None = None) -> dict:
    return {"kind": kind, "label": label, "spot_id": spot_id, "season": season,
            "difficulty": difficulty, "available_from": available_from}


def next_season(missing: list[str], current: datetime) -> tuple[str, str]:
    """Choose the nearest missing season, never an expired game ID."""
    today = local_time(current).date()
    present = season_at(current)
    if present in missing:
        return present, today.isoformat()
    months = {"spring": 3, "summer": 6, "autumn": 9, "winter": 12}
    candidates = []
    for season in missing:
        start = date(today.year, months[season], 1)
        if start < today:
            start = date(today.year + 1, months[season], 1)
        candidates.append((start, season))
    start, season = min(candidates)
    return season, start.isoformat()


def trophy(trophy_id: str, set_id: str, title: str, description: str, motif: str,
           count: int, thresholds: tuple[int, ...], dates: dict[int, str | None], unit: str,
           stage_titles: tuple[str, ...], missing: str, next_action: dict | None) -> dict[str, Any]:
    completed = count >= thresholds[-1]
    target = next((threshold for threshold in thresholds if count < threshold), thresholds[-1])
    earned_at = dates[thresholds[0]]
    return {
        "id": trophy_id, "set_id": set_id, "title": title, "description": description, "motif": motif,
        "status": "earned" if earned_at else "progress" if count else "locked",
        "completed": completed, "earned_at": earned_at,
        "progress": {"current": min(count, target), "target": target, "unit": unit},
        "stages": [{"id": f"{trophy_id}-{threshold}", "title": stage_title, "target": threshold,
                    "current": min(count, threshold), "completed": count >= threshold,
                    "earned_at": dates[threshold]} for threshold, stage_title in zip(thresholds, stage_titles)],
        "missing_conditions": [] if completed else [missing],
        "next_action": None if completed else next_action,
    }


def derive_collection(visits: list[dict], attempts: list[dict], target_id: str | None,
                      current: datetime) -> dict[str, Any]:
    """Input is one user's historical evidence, not plans or client claims."""
    current = local_time(current)
    today = current.date()
    trophies = []
    by_spot = {spot: [row for row in visits if row["spot_id"] == spot] for spot in PLACE_NAMES}
    completed = [row for row in attempts if row["status"] == "completed" and row["completed_at"]
                 and row["spot_id"] == "watergate"]
    for spot, name in PLACE_NAMES.items():
        points = first_per_key(by_spot[spot], "visit_day", "visited_at")
        trophies.append(trophy(
            f"place-{spot}", "places", PLACE_TITLES[spot], f"{name}で訪問を記録する。", spot,
            min(len(points), 1), (1,), milestones(points, (1,)), "か所", ("訪問のしるし",),
            f"{name}で訪問を1回記録する。", action("visit", f"{name}で訪問を記録する", spot, available_from=today.isoformat()),
        ))
    for season in SEASONS:
        rows = [row for row in completed if row["season"] == season]
        points = sorted(row["completed_at"] for row in rows)
        chosen, available = next_season([season], current)
        trophies.append(trophy(
            f"season-{season}", "seasons", SEASON_TITLES[season], f"{SEASON_NAMES[season]}の水門の謎を一つ解く。難易度はどちらでもよい。", season,
            min(len(points), 1), (1,), milestones(points, (1,)), "問", (f"{SEASON_NAMES[season]}の水路を開く",),
            f"{SEASON_NAMES[season]}に水門を訪れ、謎を一つ解く。",
            action("puzzle" if chosen == season_at(current) else "season", f"{SEASON_NAMES[season]}の水門を解く", "watergate",
                   season=season, difficulty="beginner", available_from=available),
        ))

    # Different-day returns to the SAME spot; multiple spots on one day cannot
    # manufacture a return, and the first threshold time may come from any spot.
    days_by_spot = {spot: first_per_key(rows, "visit_day", "visited_at") for spot, rows in by_spot.items()}
    return_spot = max(PLACE_NAMES, key=lambda spot: len(days_by_spot[spot]))
    count = len(days_by_spot[return_spot])
    thresholds = (2, 3, 5)
    dates = {}
    for threshold in thresholds:
        eligible = [points[threshold - 1] for points in days_by_spot.values() if len(points) >= threshold]
        dates[threshold] = min(eligible) if eligible else None
    next_day = max([today] + [date.fromisoformat(row["visit_day"]) + timedelta(days=1) for row in by_spot[return_spot]])
    target = next((value for value in thresholds if count < value), thresholds[-1])
    trophies.append(trophy(
        "return-path", "journeys", "また来た道", "同じ場所への別日の訪問を重ねる。", "return", count, thresholds, dates, "日",
        ("ふたたび", "なじみの道", "通い道"), f"{PLACE_NAMES[return_spot]}で、別の日にあと{max(0, target - count)}回訪問を記録する。",
        action("visit", f"{PLACE_NAMES[return_spot]}を別の日に訪れる", return_spot, available_from=next_day.isoformat()),
    ))

    coast_rows = [{**row, "season": season_at(datetime.fromisoformat(row["visited_at"]))} for row in by_spot["coast"]]
    points = first_per_key(coast_rows, "season", "visited_at")
    missing_seasons = [season for season in SEASONS if season not in {row["season"] for row in coast_rows}]
    coast_action = None
    if missing_seasons:
        season, available = next_season(missing_seasons, current)
        coast_action = action("visit" if season == season_at(current) else "season", f"{SEASON_NAMES[season]}の凪の海辺を訪れる", "coast", season=season, available_from=available)
    trophies.append(trophy(
        "coast-seasons", "journeys", "海辺の四季帳", "年をまたいでも、季節の違う海辺の訪問を集める。", "coast-seasons",
        len(points), (2, 3, 4), milestones(points, (2, 3, 4)), "季節", ("二つの海", "三つの海", "四季の海"),
        "まだ記録していない季節の海辺を訪れる：" + "・".join(SEASON_NAMES[season] for season in missing_seasons) + "。", coast_action,
    ))

    conference_days = [row["visit_day"] for row in by_spot["conference"]]
    first_conference = min(conference_days) if conference_days else None
    detours = [row for row in visits if row["spot_id"] in PLACE_NAMES and row["spot_id"] != "conference"
               and first_conference is not None and row["visit_day"] > first_conference]
    points = first_per_key(detours, "visit_day", "visited_at")
    if first_conference is None:
        detour_action = action("visit", "水都国際会議館で訪問を記録する", "conference", available_from=today.isoformat())
        detour_missing = "まず水都国際会議館を訪れ、その後の別の日に会議館以外を訪れる。"
    else:
        earliest = max([today, date.fromisoformat(first_conference) + timedelta(days=1)]
                       + [date.fromisoformat(row["visit_day"]) + timedelta(days=1) for row in detours])
        detour_action = action("visit", "別の日に四季の水門を訪れる", "watergate", available_from=earliest.isoformat())
        detour_missing = "会議館を訪れた日より後の、まだ記録のない日に会議館以外を訪れる。"
    trophies.append(trophy(
        "conference-detour", "journeys", "会議館から続く旅", "会議館の訪問後、別の日にまちの場所を訪れる。会議への参加は条件にしない。", "conference-detour",
        len(points), (1, 2, 3), milestones(points, (1, 2, 3)), "日", ("まちへの一歩", "まちへの寄り道", "まちへ通う"), detour_missing, detour_action,
    ))

    advanced = [row for row in completed if row["difficulty"] == "advanced"]
    points = first_per_key(advanced, "season", "completed_at")
    missing_seasons = [season for season in SEASONS if season not in {row["season"] for row in advanced}]
    mastery_action = None
    if missing_seasons:
        season, available = next_season(missing_seasons, current)
        mastery_action = action("puzzle" if season == season_at(current) else "season", f"{SEASON_NAMES[season]}の奥の水路を解く", "watergate",
                                season=season, difficulty="advanced", available_from=available)
    trophies.append(trophy(
        "watergate-mastery", "journeys", "奥の水路の鍵束", "異なる季節の奥の水路を解き、鍵をそろえる。", "mastery",
        len(points), (1, 2, 4), milestones(points, (1, 2, 4)), "季節", ("一つの鍵", "二つの鍵", "四季の鍵束"),
        "まだ解いていない季節の奥の水路を解く：" + "・".join(SEASON_NAMES[season] for season in missing_seasons) + "。", mastery_action,
    ))

    sets = []
    for set_id, title, reward in SET_DEFINITIONS:
        members = [item for item in trophies if item["set_id"] == set_id]
        all_completed = all(item["completed"] for item in members)
        sets.append({"id": set_id, "title": title, "reward_label": reward, "earned": sum(item["completed"] for item in members),
                     "total": len(members), "completed": all_completed,
                     "earned_at": max(item["stages"][-1]["earned_at"] for item in members) if all_completed else None})
    return {"definition_version": "1", "target_id": target_id,
            "summary": {"earned": sum(item["earned_at"] is not None for item in trophies), "total": len(trophies),
                        "completed_sets": sum(item["completed"] for item in sets)}, "sets": sets, "trophies": trophies}
