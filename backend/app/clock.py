from datetime import datetime, timedelta, timezone


JST = timezone(timedelta(hours=9), "Asia/Tokyo")
SEASONS = ("spring", "summer", "autumn", "winter")
SEASON_NAMES = {"spring": "春", "summer": "夏", "autumn": "秋", "winter": "冬"}


def now() -> datetime:
    return datetime.now(JST)


def local_time(value: datetime) -> datetime:
    if value.tzinfo is None:
        raise ValueError("Clock must return a timezone-aware datetime")
    return value.astimezone(JST)


def season_at(value: datetime) -> str:
    month = local_time(value).month
    return "spring" if 3 <= month <= 5 else "summer" if 6 <= month <= 8 else "autumn" if 9 <= month <= 11 else "winter"


def season_year(value: datetime) -> int:
    value = local_time(value)
    return value.year - 1 if value.month <= 2 else value.year


def catalog_year(value: datetime, season: str) -> int:
    value = local_time(value)
    return value.year - 1 if season == "winter" and value.month <= 2 else value.year
