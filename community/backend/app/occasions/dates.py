"""Date-only occasions use Japan's calendar and never require a birth year."""

from datetime import date, datetime, timedelta, timezone
import calendar

JST = timezone(timedelta(hours=9))
SUGGESTION_WINDOW_DAYS = 30


def today_jst(current: datetime | None = None) -> date:
    current = current or datetime.now(timezone.utc)
    if current.tzinfo is None or current.utcoffset() is None:
        raise ValueError("An aware timestamp is required")
    return current.astimezone(JST).date()


def validate_occasion_date(month: int, day: int, *, repeats_annually: bool, year: int | None = None) -> None:
    if type(month) is not int or type(day) is not int or type(repeats_annually) is not bool:
        raise ValueError("Use an integer month/day and a repeat flag")
    if repeats_annually:
        # 2000 admits February 29 without recording or inferring a birth year.
        date(2000, month, day)
    else:
        if type(year) is not int:
            raise ValueError("A one-time occasion requires a year")
        date(year, month, day)


def next_occurrence(
    month: int,
    day: int,
    *,
    repeats_annually: bool,
    year: int | None = None,
    current_date: date | None = None,
    window_days: int = SUGGESTION_WINDOW_DAYS,
) -> dict | None:
    """Return the nearest occurrence within the inclusive [today, today+30] window.

    February 29 is observed on February 28 in non-leap years. The stored month/day
    stays unchanged; occurrence_year identifies the yearly instance for deduping.
    """
    validate_occasion_date(month, day, repeats_annually=repeats_annually, year=year)
    if type(window_days) is not int or not 0 <= window_days <= 366:
        raise ValueError("The window must contain 0 to 366 days")
    current_date = current_date or today_jst()
    if type(current_date) is not date:
        raise ValueError("Use a calendar date")

    def in_year(target_year: int) -> tuple[date, bool]:
        adjusted = month == 2 and day == 29 and not calendar.isleap(target_year)
        return date(target_year, month, 28 if adjusted else day), adjusted

    if repeats_annually:
        occurrence, adjusted = in_year(current_date.year)
        if occurrence < current_date:
            if current_date.year == date.max.year:
                return None
            occurrence, adjusted = in_year(current_date.year + 1)
    else:
        occurrence, adjusted = date(year, month, day), False
    remaining = (occurrence - current_date).days
    if remaining < 0 or remaining > window_days:
        return None
    return {
        "occurrence_date": occurrence.isoformat(),
        "occurrence_year": occurrence.year,
        "days_until": remaining,
        "leap_adjusted": adjusted,
    }
