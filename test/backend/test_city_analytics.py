import json
from datetime import timedelta

import pytest
from app.analytics import city_scope
from app.residence.schemas import ResidenceUpdate
from app.residence.service import ResidenceService
from test_provider_analytics import NOW, analytics, consult, outing
from test_residence import profiles

__all__ = ['analytics']


@pytest.fixture
def city(analytics, monkeypatch):
    monkeypatch.setattr(city_scope, 'clock_now', lambda: NOW)
    with analytics.app.state.database.transaction(True) as conn:
        for pid in ('forest-house', 'shore-school'):
            conn.execute("INSERT INTO settings VALUES(?, '1') ON CONFLICT(key) DO UPDATE SET value='1'",
                         (city_scope.REGISTRY_PREFIX + pid,))
    return analytics


def visit(city, key, *, route='osaka-nnishi-reference', **values):
    outing(city, key, **values)
    with city.app.state.database.transaction(True) as conn:
        conn.execute('UPDATE daytrip_outings SET route_json=? WHERE id=?',
                     (json.dumps(dict(id=route, destination='N西市（文字列だけでは対象にしない）')), key))


def get(city, days=30):
    response = city.client('forest').get(f'/providers/forest-house/city-analytics?days={days}')
    assert response.status_code == 200, response.text
    return response.json()


def test_staff_and_explicit_city_registration_are_both_required(city):
    path = '/providers/forest-house/city-analytics'
    assert city.client().get(path).status_code == 401
    assert city.client('aoi').get(path).status_code == 404
    assert city.client('shore').get(path).status_code == 404
    forest = city.client('forest')
    assert forest.get(path).status_code == 200
    with city.app.state.database.transaction(True) as conn:
        conn.execute("UPDATE providers SET area='N西市',name='N西市という表示名' WHERE id='forest-house'")
        conn.execute('UPDATE settings SET value=? WHERE key=?', ('0', city_scope.REGISTRY_PREFIX + 'forest-house'))
    assert forest.get(path).status_code == 404
    with city.app.state.database.transaction(True) as conn:
        conn.execute('UPDATE settings SET value=? WHERE key=?', ('1', city_scope.REGISTRY_PREFIX + 'forest-house'))
        conn.execute("UPDATE provider_staff SET active=0 WHERE user_id='provider-forest'")
    assert forest.get(path).status_code == 404
    with city.app.state.database.transaction(True) as conn:
        conn.execute("UPDATE provider_staff SET active=1 WHERE user_id='provider-forest'")
        conn.execute("UPDATE providers SET active=0 WHERE id='forest-house'")
    assert forest.get(path).status_code == 404


@pytest.mark.parametrize('days', [30, 90, 365])
def test_empty_period_is_zero_and_unknown_query_is_rejected(city, days):
    data = get(city, days)
    assert data['scope'] == 'city' and data['city']['id'] == 'n-nishi'
    assert data['provider_count'] == 2 and data['published_plan_count'] == 3
    assert data['period']['timezone'] == 'Asia/Tokyo'
    assert len(data['daily']['items']) == days
    assert all(row['count'] == row['previous_count'] == 0 for row in data['summary'].values())
    assert data['daily']['status'] == data['trend']['status'] == data['origins']['status'] == 'no_data'
    assert data['origins']['areas'] == [] and data['trend']['items']
    assert all(row['visitors'] == 0 for row in data['providers']['items'])
    assert all('plan_count' in row for row in data['plan_categories'])


def test_only_fixed_days_are_accepted(city):
    client = city.client('forest')
    for query in ('days=31', 'days=-1', 'days=true', 'days=30&area=27100',
                  'days=30&provider_ids=forest-house', 'days=30&sql=SELECT', 'days=30&start_date=2020-01-01'):
        assert client.get('/providers/forest-house/city-analytics?' + query).status_code == 422


def test_same_jst_day_other_provider_is_circulation_not_returning(city):
    users = tuple(range(5))
    profiles(city, users)
    visit(city, 'morning', users=users, ended='2026-11-08T15:30:00+00:00')
    visit(city, 'evening', users=users, provider='shore-school', ended='2026-11-09T14:30:00+00:00')
    consult(city, 'private-conditions')
    data = get(city)
    assert {key: metric['count'] for key, metric in data['summary'].items()} == dict(
        visitors=5, returning_visitors=0, visit_days=5, participations=10)
    assert sum(row['visitors'] for row in data['providers']['items']) == 10
    row = data['origins']['areas'][0]
    assert (row['visitors'], row['returning_visitors'], row['visits']) == (5, 0, 10)
    assert [day['date'] for day in data['daily']['items'] if day['visitors']] == ['2026-11-09']
    serialized = json.dumps(data, ensure_ascii=False)
    for private in ('analytics-0', '非公開', 'snapshot', 'shared_conditions', 'price_yen', 'u-aoi'):
        assert private not in serialized


def test_different_jst_days_on_same_utc_day_are_city_returning(city):
    users = tuple(range(5))
    visit(city, 'before-midnight', users=users, ended='2026-11-08T14:30:00+00:00')
    visit(city, 'after-midnight', users=users, provider='shore-school', ended='2026-11-08T15:30:00+00:00')
    data = get(city)
    assert data['summary']['visitors']['count'] == data['summary']['returning_visitors']['count'] == 5
    assert data['summary']['visit_days']['count'] == data['summary']['participations']['count'] == 10


def test_return_history_before_window_counts_but_other_region_or_old_route_does_not(city):
    users = tuple(range(5))
    visit(city, 'old-city', users=users, provider='shore-school', ended=(NOW - timedelta(days=400)).isoformat())
    visit(city, 'current', users=users)
    assert get(city)['summary']['returning_visitors']['count'] == 5
    with city.app.state.database.transaction(True) as conn:
        conn.execute('UPDATE settings SET value=? WHERE key=?', ('0', city_scope.REGISTRY_PREFIX + 'shore-school'))
    assert get(city)['summary']['returning_visitors']['count'] == 0
    with city.app.state.database.transaction(True) as conn:
        conn.execute('UPDATE settings SET value=? WHERE key=?', ('1', city_scope.REGISTRY_PREFIX + 'shore-school'))
        conn.execute("UPDATE daytrip_outings SET route_json=? WHERE id='old-city'",
                     (json.dumps(dict(id='shinjuku-machida-rail', destination='N西市')),))
    data = get(city)
    assert data['summary']['returning_visitors']['count'] == 0
    assert data['summary']['participations']['count'] == 5


def test_jst_period_boundaries_and_naive_invalid_future_dates(city):
    users = tuple(range(5))
    for key, ended in (
        ('previous-start', '2026-09-11T15:00:00+00:00'),
        ('previous-end', '2026-10-11T14:59:59.999999+00:00'),
        ('current-start', '2026-10-11T15:00:00+00:00'),
        ('current-end', NOW.isoformat()),
        ('future', (NOW + timedelta(microseconds=1)).isoformat()),
        ('invalid', '2026-11-99T00:00:00+09:00'),
        ('naive', '2026-11-09T12:00:00'),
    ):
        visit(city, key, users=users, ended=ended)
    data = get(city)
    assert data['period']['start_date'] == '2026-10-12'
    assert data['summary']['participations']['count'] == data['summary']['participations']['previous_count'] == 10
    assert data['summary']['visitors']['count'] == 5
    assert data['summary']['returning_visitors']['count'] == 5


def test_unconfirmed_cancelled_and_revoked_witness_are_excluded(city):
    users = tuple(range(5))
    visit(city, 'valid', users=users)
    visit(city, 'cancelled', users=users, status='cancelled')
    visit(city, 'unverified', users=users)
    visit(city, 'withdrawn', users=users)
    with city.app.state.database.transaction(True) as conn:
        conn.execute("UPDATE daytrip_participants SET provider_verified=0 WHERE outing_id='unverified'")
        conn.execute("UPDATE daytrip_participants SET revoked=1 WHERE outing_id='withdrawn'")
    assert get(city)['summary']['participations']['count'] == 5
    # Revoking one witness also makes its confirmation invalid; the remaining
    # cohort is below the city threshold and must be hidden, never shown as zero.
    with city.app.state.database.transaction(True) as conn:
        conn.execute("UPDATE daytrip_participants SET revoked=1 WHERE outing_id='valid' AND user_id='analytics-0'")
    data = get(city)
    assert data['summary']['visitors']['count'] is None
    assert data['origins']['areas'] == []
    assert all(row['visitors'] is None for row in data['providers']['items'])


def test_provider_atomic_groups_prevent_own_total_subtraction(city):
    visit(city, 'a', users=tuple(range(6)))
    visit(city, 'b', users=tuple(range(1, 11)), provider='shore-school')
    # A-only=1, B-only=5, A+B=5: both provider totals meet five, but their
    # union would expose a one-person group to a provider with its own totals.
    data = get(city)
    assert all(metric['count'] is None and metric['change_count'] is None for metric in data['summary'].values())
    assert data['providers']['status'] == 'insufficient_sample'
    assert all(row['visitors'] is None and row['participations'] is None for row in data['providers']['items'])
    assert data['provider_count'] == 2 and len(data['providers']['items']) == 2
    assert data['origins']['total_visitors'] is None
    assert all(row['visitors'] is None for row in data['daily']['items'])


def test_small_daily_cells_are_coarsened_not_zeroed(city):
    visit(city, 'three-first', users=(0, 1, 2), ended=(NOW - timedelta(days=2)).isoformat())
    visit(city, 'three-next', users=(3, 4, 5), ended=(NOW - timedelta(days=1)).isoformat())
    data = get(city)
    assert data['summary']['visitors']['count'] == 6
    assert data['daily']['status'] == 'insufficient_sample'
    assert all(row['visitors'] is None for row in data['daily']['items'])
    assert data['trend']['status'] == 'available' and data['trend']['interval_days'] in (14, 30)
    assert sum(row['participations'] for row in data['trend']['items']) == 6
    assert all(row['visitors'] == 0 or row['visitors'] >= 5 for row in data['trend']['items'])


def test_small_returning_or_first_time_cohort_hides_all_period_metrics(city):
    visit(city, 'current', users=tuple(range(6)))
    visit(city, 'prior', users=(0, 1), ended=(NOW - timedelta(days=2)).isoformat())
    data = get(city)
    assert all(metric['count'] is None for metric in data['summary'].values())
    assert data['trend']['status'] == 'insufficient_sample' and not data['trend']['items']
    assert data['origins']['areas'] == []


def test_city_map_withdrawal_and_deletion_suppress_the_complete_breakdown(city):
    users = tuple(range(6))
    profiles(city, users)
    visit(city, 'current', users=users)
    assert get(city)['origins']['areas'][0]['visitors'] == 6
    residence = ResidenceService(city.app.state.database)
    residence.me('analytics-0', ResidenceUpdate(residence_area_id='27100', share_area_analytics=False, version=1))
    data = get(city)['origins']
    assert data['status'] == 'insufficient_sample' and data['areas'] == []
    assert data['total_visitors'] == 6
    assert data['withheld_visitors'] is None and data['consented_visitors'] is None
    residence.me('analytics-0', ResidenceUpdate(residence_area_id=None, share_area_analytics=False, version=2))
    assert get(city)['origins']['missing_visitors'] is None
    # A different one-person residence cannot be inferred from a partial map.
    residence.me('analytics-0', ResidenceUpdate(residence_area_id='13104', share_area_analytics=True, version=3))
    assert get(city)['origins']['areas'] == []
    with city.app.state.database.transaction(True) as conn:
        conn.execute("UPDATE users SET login_enabled=0 WHERE id='analytics-0'")
    data = get(city)
    # Four remaining valid witnesses are now a protected small group.
    assert data['summary']['visitors']['count'] is None


def test_safe_missing_group_is_explicit_without_private_ids(city):
    profiles(city, range(5))
    visit(city, 'ten', users=tuple(range(10)))
    data = get(city)['origins']
    assert data['total_visitors'] == 10 and data['missing_visitors'] == data['consented_visitors'] == 5
    assert data['withheld_visitors'] == 0 and data['areas'][0]['visitors'] == 5
    assert 'analytics-' not in json.dumps(data)


def test_unregistered_provider_public_plans_and_visits_are_absent(city):
    visit(city, 'forest', users=tuple(range(5)))
    visit(city, 'shore', users=tuple(range(5, 10)), provider='shore-school')
    with city.app.state.database.transaction(True) as conn:
        conn.execute('UPDATE settings SET value=? WHERE key=?', ('0', city_scope.REGISTRY_PREFIX + 'shore-school'))
    data = get(city)
    assert data['provider_count'] == 1 and data['published_plan_count'] == 2
    assert data['summary']['visitors']['count'] == 5
    assert [row['id'] for row in data['providers']['items']] == ['forest-house']
    assert next(row['plan_count'] for row in data['plan_categories'] if row['id'] == 'coast') == 0


def test_city_read_is_read_only_and_leaves_self_analytics_unchanged(city):
    visit(city, 'current', users=tuple(range(5)))
    consult(city, 'private-conditions')
    client = city.client('forest')
    self_before = client.get('/providers/forest-house/analytics?days=30').json()
    with city.app.state.database.transaction() as conn:
        before = list(conn.iterdump())
    assert client.get('/providers/forest-house/city-analytics?days=30').status_code == 200
    assert client.get('/providers/forest-house/analytics?days=30').json() == self_before
    with city.app.state.database.transaction() as conn:
        assert list(conn.iterdump()) == before


def test_fictional_pack_has_city_union_and_safe_adaptive_trend(city):
    from app.enrichment import enrich

    enrich(city.app.state.database, city.settings, NOW)
    data = get(city, 90)
    assert {key: value['count'] for key, value in data['summary'].items()} == dict(
        visitors=36, returning_visitors=36, visit_days=144, participations=144)
    assert data['provider_count'] == 2 and data['published_plan_count'] == 15
    assert data['origins']['consented_visitors'] == 36
    assert len(data['origins']['areas']) == 6
    assert data['trend']['status'] == 'available'
    assert sum(row['participations'] for row in data['trend']['items']) == 144
    assert all(row['visitors'] == 0 or row['visitors'] >= 5 for row in data['trend']['items'])
