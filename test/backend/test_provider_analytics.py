import json
from datetime import UTC, datetime, timedelta

import pytest
from app.analytics import service as module

NOW = datetime(2026, 11, 10, 3, tzinfo=UTC)
CONDITIONS = dict(planned_people=4, nights=0, budget_yen=6000,
                  budget_basis='per_person', budget_scope='plan_only', date_start='2026-11-10')


@pytest.fixture
def analytics(harness, monkeypatch):
    monkeypatch.setattr(module, 'clock_now', lambda: NOW)
    with harness.app.state.database.transaction(True) as conn:
        for index in range(12):
            conn.execute('''INSERT INTO users SELECT ?,?,?,'集','#000000',salt,password_hash,1
                FROM users WHERE id='u-aoi' ''', (f'analytics-{index}', f'analytics-{index}', '非公開氏名'))
    return harness


def consult(harness, key, *, sharer=0, created=None, conditions=None, provider='forest-house', status='open', snapshot=None):
    created = created or (NOW - timedelta(days=1)).isoformat()
    plan = 'forest-day' if provider == 'forest-house' else 'shore-school'
    body = snapshot if snapshot is not None else dict(shared_conditions=CONDITIONS if conditions is None else conditions,
        share_note='非公開相談文', internal_message='非公開内部会話', photo='非公開写真', interests=['private-interest'])
    with harness.app.state.database.transaction(True) as conn:
        conn.execute("INSERT INTO travel_parties VALUES(?,'peers',NULL,?,?,'open',?)",
            ('party-' + key, f'analytics-{sharer}', '非公開講名', created))
        conn.execute("INSERT INTO plan_selections VALUES(?,?,?,?,?,?,'active',?)",
            ('selection-' + key, 'party-' + key, plan, provider, json.dumps(body), f'analytics-{sharer}', created))
        conn.execute('INSERT INTO consultations VALUES(?,?,?,1,?)', ('consult-' + key, 'selection-' + key, status, created))


def outing(harness, key, *, users=(0, 1), ended=None, provider='forest-house', status='confirmed', changes=None):
    ended = ended or (NOW - timedelta(days=1)).isoformat()
    parsed = module.timestamp(ended)
    started = (parsed - timedelta(hours=4)).isoformat() if parsed else 'invalid'
    plan = 'forest-day' if provider == 'forest-house' else 'shore-school'
    with harness.app.state.database.transaction(True) as conn:
        conn.execute("INSERT INTO travel_parties VALUES(?,'peers',NULL,?,?,'open',?)",
            ('trip-' + key, f'analytics-{users[0]}', '非公開開催講', started))
        conn.execute('''INSERT INTO daytrip_outings
            (id,circle_id,title,route_json,starts_at,ends_at,day,status,leader_id,leader_accepted,
             plan_id,provider_id,plan_json,created_by,created_at)
            VALUES(?,?,?,'{}',?,?,?,?,?,1,?,?,'{}',?,?)''',
            (key, 'trip-' + key, '非公開開催名', started, ended, '2026-11-09', status,
             f'analytics-{users[0]}', plan, provider, f'analytics-{users[0]}', started))
        for index, user in enumerate(users):
            values = dict(accepted=1, claimed=1, full_route=1, confirmed_by=f'analytics-{users[(index + 1) % len(users)]}',
                          provider_verified=1, points=123, revoked=0)
            if changes and index == 0:
                values.update(changes)
            conn.execute('INSERT INTO daytrip_participants VALUES(?,?,?,?,?,?,?,?,?)',
                (key, f'analytics-{user}', *values.values()))


def result(harness, days=30, username='forest'):
    response = harness.client(username).get(f'/providers/forest-house/analytics?days={days}')
    assert response.status_code == 200, response.text
    return response.json()


def test_authorization_provider_scope_and_revocation(analytics):
    path = '/providers/forest-house/analytics'
    assert analytics.client().get(path).status_code == 401
    for username in ('aoi', 'shore'):
        assert analytics.client(username).get(path).status_code == 404
    forest = analytics.client('forest')
    assert forest.get('/providers/missing/analytics').status_code == 404
    assert forest.get(path).status_code == 200
    with analytics.app.state.database.transaction(True) as conn:
        conn.execute("UPDATE provider_staff SET active=0 WHERE provider_id='forest-house'")
    assert forest.get(path).status_code == 404
    with analytics.app.state.database.transaction(True) as conn:
        conn.execute("UPDATE provider_staff SET active=1 WHERE provider_id='forest-house'")
        conn.execute("UPDATE providers SET active=0 WHERE id='forest-house'")
    assert forest.get(path).status_code == 404


@pytest.mark.parametrize('days', [30, 90, 365])
def test_periods_empty_values_and_zero_filled_days(analytics, days):
    data = result(analytics, days)
    assert data['period']['timezone'] == 'Asia/Tokyo'
    assert data['period']['end_date'] == '2026-11-10'
    assert len(data['daily']) == days
    assert data['daily'][-1]['date'] == data['period']['end_date']
    assert data['daily'][0]['date'] == data['period']['start_date']
    assert all(metric['count'] == metric['previous_count'] == 0 for metric in data['summary'].values())
    assert all(metric['change_percent'] is None for metric in data['summary'].values())
    assert data['conditions']['sample_count'] == 0
    assert data['conditions']['people']['status'] == 'no_data'
    assert data['plans'] and all(row['consultations'] == 0 for row in data['plans'])
    assert all(row['status'] == 'not_collected' for row in data['demographics'].values())


def test_bounded_query_rejects_arbitrary_filters(analytics):
    client = analytics.client('forest')
    for query in ('days=0', 'days=31', 'days=366', 'days=-30', 'days=true', 'days=30.5', 'days=NaN',
                  'days=30&sql=select', 'days=30&start_date=2026-01-01', 'days=30&provider_id=shore-school'):
        assert client.get('/providers/forest-house/analytics?' + query).status_code == 422, query
    assert client.get('/providers/forest-house/analytics').status_code == 200


def test_jst_boundaries_previous_period_dates_and_future_exclusion(analytics):
    dates = {
        'before': '2026-09-11T23:59:59.999999+09:00',
        'previous-first': '2026-09-12T00:00:00+09:00',
        'previous-last': '2026-10-11T23:59:59.999999+09:00',
        'current-first': '2026-10-11T15:00:00+00:00',
        'current-last': NOW.isoformat(),
        'future': (NOW + timedelta(microseconds=1)).isoformat(),
        'invalid': '2026-11-99T00:00:00+09:00',
        'naive': '2026-11-09T00:00:00',
    }
    for key, date in dates.items():
        consult(analytics, key, created=date)
    data = result(analytics)
    assert data['period']['start_date'] == '2026-10-12'
    assert data['period']['previous_start_date'] == '2026-09-12'
    assert data['period']['previous_end_date'] == '2026-10-11'
    metric = data['summary']['consultations']
    assert (metric['count'], metric['previous_count'], metric['change_percent']) == (2, 2, 0)
    assert data['daily'][0]['consultations'] == data['daily'][-1]['consultations'] == 1


def test_real_unique_users_visits_and_same_invitation_not_counted_twice(analytics):
    consult(analytics, 'one')
    consult(analytics, 'foreign', provider='shore-school')
    with analytics.app.state.database.transaction(True) as conn:
        conn.execute("INSERT INTO circle_provider_invitations VALUES('invitation','party-one','forest-house','analytics-0','{}','accepted',1,'consult-one',?,?)", (NOW.isoformat(), NOW.isoformat()))
    outing(analytics, 'first')
    outing(analytics, 'repeat', ended=(NOW - timedelta(days=2)).isoformat())
    outing(analytics, 'foreign', users=(2, 3), provider='shore-school')
    # A correction/reconfirmation ledger can have multiple rows; it must never multiply usage.
    with analytics.app.state.database.transaction(True) as conn:
        for index, points in enumerate((100, -100, 100)):
            conn.execute("INSERT INTO daytrip_ledger VALUES(?,'first','analytics-0','award',?,?,?,'v1',?)",
                (f'ledger-{index}', points, points, '非公開訂正理由', NOW.isoformat()))
    data = result(analytics)
    assert {key: value['count'] for key, value in data['summary'].items()} == dict(
        consultations=1, confirmed_users=2, confirmed_visits=4, completed_outings=2)
    assert sum(row['confirmed_users'] for row in data['daily']) == 4
    assert {row['id'] for row in data['plans']} == {'forest-day', 'forest-six'}
    assert next(row for row in data['plans'] if row['id'] == 'forest-day')['confirmed_visits'] == 4
    serialized = json.dumps(data, ensure_ascii=False)
    assert '非公開' not in serialized
    assert 'analytics-0' not in serialized and 'shore-school' not in serialized
    assert 'private-interest' not in serialized


def test_only_ended_mutually_and_provider_confirmed_participation_counts(analytics):
    for key, change in (
        ('unaccepted', dict(accepted=0)), ('unclaimed', dict(claimed=0)),
        ('unconfirmed', dict(confirmed_by=None)), ('self', dict(confirmed_by='analytics-0')),
        ('unverified', dict(provider_verified=0)), ('revoked', dict(revoked=1)),
    ):
        outing(analytics, key, changes=change)
    outing(analytics, 'cancelled', status='cancelled')
    outing(analytics, 'future', ended=(NOW + timedelta(hours=1)).isoformat())
    outing(analytics, 'invalid', ended='2026-11-99T00:00:00+09:00')
    data = result(analytics)
    # In the three other invalid cases, the valid second participant still has a
    # witness with accepted/claimed participation. Their own confirmation stays valid.
    assert data['summary']['confirmed_visits']['count'] == 3
    assert data['summary']['confirmed_users']['count'] == 1
    assert data['summary']['completed_outings']['count'] == 3


def test_previous_usage_and_public_plan_totals_have_separate_scope(analytics):
    outing(analytics, 'old', ended='2026-10-01T12:00:00+09:00')
    outing(analytics, 'now', users=(0, 2))
    consult(analytics, 'now')
    with analytics.app.state.database.transaction(True) as conn:
        conn.execute("UPDATE provider_plans SET status='closed' WHERE id='forest-day'")
    data = result(analytics)
    assert data['summary']['confirmed_users']['count'] == 2
    assert data['summary']['confirmed_users']['previous_count'] == 2
    assert data['summary']['confirmed_users']['change_count'] == 0
    assert [row['id'] for row in data['plans']] == ['forest-six']
    assert data['summary']['consultations']['count'] == 1


def test_latest_shared_conditions_deduplicate_people_and_suppress_small_cells(analytics):
    for index in range(5):
        consult(analytics, f'old-{index}', sharer=index, created=(NOW - timedelta(days=2)).isoformat(),
                conditions=CONDITIONS | dict(planned_people=40))
        consult(analytics, f'new-{index}', sharer=index)
    data = result(analytics)['conditions']
    assert data['consultation_count'] == 10
    assert data['sample_count'] == data['unique_sharers'] == 5
    assert data['people']['status'] == 'available'
    assert next(row['count'] for row in data['people']['bins'] if row['key'] == '3-5') == 5
    consult(analytics, 'different', sharer=5, conditions=CONDITIONS | dict(planned_people=8))
    data = result(analytics)['conditions']
    assert data['sample_count'] == 6
    assert data['people']['status'] == 'insufficient_sample'
    assert all(row['count'] is None for row in data['people']['bins'])
    assert data['nights']['status'] == 'available'


def test_many_consultations_from_one_sharer_cannot_bypass_privacy_threshold(analytics):
    for index in range(8):
        consult(analytics, str(index), conditions=CONDITIONS | dict(planned_people=500))
    data = result(analytics)['conditions']
    assert data['consultation_count'] == 8 and data['sample_count'] == 1
    assert data['people']['status'] == 'insufficient_sample'
    assert all(row['count'] is None for row in data['people']['bins'])


def test_budget_basis_missing_and_malformed_snapshot_are_not_invented(analytics):
    for index in range(5):
        consult(analytics, str(index), sharer=index)
    consult(analytics, 'total', sharer=5, conditions=CONDITIONS | dict(budget_basis='party_total'))
    consult(analytics, 'whole', sharer=6, conditions=CONDITIONS | dict(budget_scope='whole_trip'))
    consult(analytics, 'malformed', sharer=7, snapshot=['bad-shape'])
    data = result(analytics)
    budget = data['conditions']['budget_per_person']
    assert budget['known_count'] == 5 and budget['missing_count'] == 3
    assert data['conditions']['people']['known_count'] == 7
    for value in data['demographics'].values():
        assert value['known_count'] == 0 and value['missing_count'] == 8
        assert value['status'] == 'not_collected'


def test_revoked_sharing_leaves_only_historical_counts(analytics):
    for index in range(5):
        consult(analytics, str(index), sharer=index)
    with analytics.app.state.database.transaction(True) as conn:
        conn.execute("UPDATE consultations SET status='closed' WHERE id='consult-0'")
        conn.execute("UPDATE plan_selections SET status='closed' WHERE id='selection-1'")
        conn.execute("UPDATE travel_parties SET status='closed' WHERE id='party-2'")
        conn.execute("UPDATE users SET login_enabled=0 WHERE id='analytics-3'")
        conn.execute("INSERT INTO circle_provider_invitations VALUES('invite-4','party-4','forest-house','analytics-4','{}','cancelled',1,'consult-4',?,NULL)", (NOW.isoformat(),))
    data = result(analytics)
    assert data['summary']['consultations']['count'] == 5
    assert data['conditions']['sample_count'] == 0


def test_bin_boundaries_are_precise_and_invalid_values_are_missing():
    assert [module.people_bin({'planned_people': value}) for value in (0, 1, 2, 3, 5, 6, 10, 11, 20, 21, 500, 501)] == [
        None, '1-2', '1-2', '3-5', '3-5', '6-10', '6-10', '11-20', '11-20', '21+', '21+', None]
    assert [module.nights_bin({'nights': value}) for value in (-1, 0, 1, 2, 3, 30, 31, True)] == [None, '0', '1', '2', '3+', '3+', None, None]
    assert [module.budget_bin(CONDITIONS | {'budget_yen': value}) for value in (0, 9999, 10000, 29999, 30000, 49999, 50000, '6000')] == [
        None, 'under-10000', '10000-29999', '10000-29999', '30000-49999', '30000-49999', '50000+', None]


def test_requested_content_pack_matches_dashboard_without_survey_or_existing_user_credit(analytics):
    from app.enrichment import enrich

    report = enrich(analytics.app.state.database, analytics.settings, NOW)
    data = result(analytics, 90)
    assert report['completed_outings'] == data['summary']['completed_outings']['count'] == 30
    assert data['summary']['consultations']['count'] == 35
    assert data['summary']['confirmed_users']['count'] == 36
    assert data['summary']['confirmed_visits']['count'] == 144
    assert data['conditions']['sample_count'] == 31
    assert data['conditions']['people']['status'] == 'available'
    assert next(row['count'] for row in data['conditions']['people']['bins'] if row['key'] == '21+') == 6
    assert all(value['status'] == 'not_collected' for value in data['demographics'].values())
    assert data['summary']['confirmed_users']['previous_count'] == 0
    assert data['origins']['total_visitors'] == data['origins']['consented_visitors'] == 36
    assert len(data['origins']['areas']) == 6
    assert all(area['visitors'] == area['returning_visitors'] == 6 for area in data['origins']['areas'])
    assert data['origins']['missing_visitors'] == data['origins']['withheld_visitors'] == 0
    with analytics.app.state.database.transaction() as conn:
        assert conn.execute("SELECT COUNT(*) FROM daytrip_participants WHERE user_id IN ('u-aoi','u-ren','u-mio')").fetchone()[0] == 0
