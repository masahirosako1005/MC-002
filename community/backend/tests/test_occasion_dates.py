from datetime import date, datetime, timezone

import pytest

from app.occasions.dates import next_occurrence, today_jst


def test_japan_day_boundary_uses_explicit_timezone():
    assert today_jst(datetime(2026, 12, 31, 14, 59, tzinfo=timezone.utc)) == date(2026, 12, 31)
    assert today_jst(datetime(2026, 12, 31, 15, 0, tzinfo=timezone.utc)) == date(2027, 1, 1)
    with pytest.raises(ValueError):
        today_jst(datetime(2026, 12, 31, 15, 0))


def test_year_boundary_and_repeated_read_have_one_stable_occurrence():
    first = next_occurrence(1, 4, repeats_annually=True, current_date=date(2026, 12, 20))
    again = next_occurrence(1, 4, repeats_annually=True, current_date=date(2027, 1, 1))
    assert first["occurrence_date"] == again["occurrence_date"] == "2027-01-04"
    assert first["occurrence_year"] == again["occurrence_year"] == 2027
    assert first["days_until"] == 15
    assert again["days_until"] == 3


def test_window_is_inclusive_and_past_annual_occurrence_does_not_repeat():
    assert next_occurrence(12, 1, repeats_annually=True, current_date=date(2026, 11, 1))["days_until"] == 30
    assert next_occurrence(12, 2, repeats_annually=True, current_date=date(2026, 11, 1)) is None
    assert next_occurrence(11, 1, repeats_annually=True, current_date=date(2026, 11, 1))["days_until"] == 0
    assert next_occurrence(10, 31, repeats_annually=True, current_date=date(2026, 11, 1)) is None


def test_leap_birthday_uses_february_28_without_changing_stored_month_day():
    assert next_occurrence(2, 29, repeats_annually=True, current_date=date(2027, 2, 27)) == {
        "occurrence_date": "2027-02-28", "occurrence_year": 2027, "days_until": 1, "leap_adjusted": True,
    }
    assert next_occurrence(2, 29, repeats_annually=True, current_date=date(2028, 2, 28)) == {
        "occurrence_date": "2028-02-29", "occurrence_year": 2028, "days_until": 1, "leap_adjusted": False,
    }
    assert next_occurrence(2, 29, repeats_annually=True, current_date=date(2027, 3, 1)) is None


def test_one_time_date_never_recurs_and_rejects_invalid_leap_day():
    assert next_occurrence(1, 4, year=2027, repeats_annually=False, current_date=date(2026, 12, 20))["occurrence_year"] == 2027
    assert next_occurrence(1, 4, year=2026, repeats_annually=False, current_date=date(2026, 12, 20)) is None
    with pytest.raises(ValueError):
        next_occurrence(2, 29, year=2027, repeats_annually=False)
    with pytest.raises(ValueError):
        next_occurrence(5, 3, repeats_annually=False)


@pytest.mark.parametrize("month,day", [(0, 1), (13, 1), (4, 31), (2, 30), (True, 1), (1, 0)])
def test_invalid_date_is_not_silently_normalized(month, day):
    with pytest.raises(ValueError):
        next_occurrence(month, day, repeats_annually=True)
