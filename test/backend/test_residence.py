import json
from concurrent.futures import ThreadPoolExecutor
from datetime import timedelta

import pytest
from app.database import password_hash
from app.residence import schema
from app.residence.catalog import AREA_BY_ID
from app.residence.schemas import Registration, ResidenceUpdate
from app.residence.service import ResidenceService
from test_provider_analytics import NOW, analytics, outing, result

# Re-exporting the existing isolated app fixture avoids creating another database.
__all__ = ['analytics']

SIGNUP = dict(username='new-traveler', password='residence-password-2026', name='新しい利用者', residence_area_id='27205')


def signup(harness, **changes):
    return harness.client().write('POST', '/register', SIGNUP | changes)


def profiles(harness, ids, area='27100', share=True):
    with harness.app.state.database.transaction(True) as conn:
        for index in ids:
            conn.execute('INSERT INTO residence_profiles VALUES(?,?,?,1,?)',
                (f'analytics-{index}', area, int(share), NOW.isoformat()))


def test_public_catalog_has_47_prefectures_and_rounded_city_points(harness):
    response = harness.client().get('/residence/areas')
    assert response.status_code == 200
    data = response.json()
    assert len(data['items']) == len(AREA_BY_ID) == 69
    assert len({row['prefecture'] for row in data['items']}) == 47
    assert all(20 < row['latitude'] < 46 and 122 < row['longitude'] < 154 for row in data['items'])
    assert all(row['latitude'] == round(row['latitude'], 2) for row in data['items'])
    assert data['destination']['fictional'] and data['destination']['name'] == 'N西市'
    assert data['precision'] == 'municipality_representative'
    assert set(('27100', '27140', '26100', '28100', '29201', '27205')) <= AREA_BY_ID.keys()
    assert 'user_id' not in response.text and 'password' not in response.text


def test_registration_is_atomic_private_and_does_not_issue_session(harness):
    anonymous = harness.client()
    response = anonymous.write('POST', '/register', SIGNUP)
    assert response.status_code == 201, response.text
    data = response.json()
    assert data['login_required'] and 'csrf_token' not in data and 'access_token' not in data
    assert 'set-cookie' not in response.headers
    assert data['residence']['area']['id'] == '27205'
    assert data['residence']['share_area_analytics'] is False and data['residence']['version'] == 1
    assert SIGNUP['password'] not in response.text
    assert anonymous.get('/residence/me').status_code == 401
    uid = data['user']['id']
    with harness.app.state.database.transaction() as conn:
        user = conn.execute('SELECT * FROM users WHERE id=?', (uid,)).fetchone()
        assert user['password_hash'] == password_hash(SIGNUP['password'], user['salt'])
        assert user['password_hash'] != SIGNUP['password']
        assert conn.execute('SELECT tags,learn_from_posts FROM preferences WHERE user_id=?', (uid,)).fetchone()[:] == ('[]', 0)
        assert conn.execute('SELECT COUNT(*) FROM memberships WHERE user_id=?', (uid,)).fetchone()[0] == 0
        assert conn.execute('SELECT COUNT(*) FROM provider_staff WHERE user_id=?', (uid,)).fetchone()[0] == 0
    login = anonymous.write('POST', '/login', {'username': SIGNUP['username'], 'password': SIGNUP['password']})
    assert login.status_code == 200
    anonymous.client.headers['X-CSRF-Token'] = login.json()['csrf_token']
    assert anonymous.get('/residence/me').json() == data['residence']
    stage = harness.client()
    token = stage.write('POST', '/stage/login', {'username': SIGNUP['username'], 'password': SIGNUP['password']})
    assert token.status_code == 200 and 'set-cookie' not in token.headers
    stage.client.headers['Authorization'] = 'Bearer ' + token.json()['access_token']
    assert stage.get('/residence/me').json()['area']['id'] == '27205'


def test_registration_validation_duplicate_and_no_exact_address_fields(harness):
    for changes in ({'username': 'Aoi'}, {'username': 'a!'}, {'password': 'short'}, {'name': '\n'},
                    {'name': 'A\nB'}, {'residence_area_id': '99999'}, {'share_area_analytics': 'true'},
                    {'address': '番地は保存しない'}, {'latitude': 34.123456}, {'user_id': 'u-aoi'},
                    {'role': 'provider'}):
        assert signup(harness, **changes).status_code == 422, changes.keys()
    before = harness.client('aoi').get('/me').json()['user']
    assert signup(harness, username='aoi').status_code == 409
    assert harness.client('aoi').get('/me').json()['user'] == before
    assert signup(harness).status_code == 201
    assert signup(harness).status_code == 409


def test_unlisted_residence_can_be_left_unset_without_blocking_registration(harness):
    invalid = signup(harness, residence_area_id=None, share_area_analytics=True)
    assert invalid.status_code == 422
    saved = signup(harness, residence_area_id=None)
    assert saved.status_code == 201
    assert saved.json()['residence']['area'] is None
    assert saved.json()['residence']['share_area_analytics'] is False


def test_signup_origin_existing_session_csrf_and_rate_limit(harness):
    client = harness.client()
    assert client.write('POST', '/register', SIGNUP, headers={'Origin': 'https://untrusted.example'}).status_code == 403
    signed = harness.client('aoi')
    assert signed.write('POST', '/register', SIGNUP, headers={'X-CSRF-Token': 'bad'}).status_code == 403
    # The existing login and signup limit is shared; invalid attempts still count.
    responses = [client.write('POST', '/register', SIGNUP | {'password': 'short'}).status_code for _ in range(21)]
    assert responses[-1] == 429 and 422 in responses


def test_profile_is_owner_only_opt_in_cas_and_withdrawal(harness):
    aoi, ren = harness.client('aoi'), harness.client('ren')
    empty = aoi.get('/residence/me').json()
    assert empty == dict(area=None, share_area_analytics=False, version=0, updated_at=None)
    body = dict(residence_area_id='27100', share_area_analytics=True, version=0)
    assert aoi.write('PUT', '/residence/me', body, headers={'X-CSRF-Token': 'bad'}).status_code == 403
    response = aoi.write('PUT', '/residence/me', body)
    assert response.status_code == 200 and response.json()['share_area_analytics']
    assert aoi.write('PUT', '/residence/me', body).status_code == 409
    assert ren.get('/residence/me?user_id=u-aoi').json() == empty
    assert ren.get('/residence/u-aoi').status_code == 404
    assert ren.write('PUT', '/residence/me', body | {'user_id': 'u-aoi'}).status_code == 422
    assert aoi.write('PUT', '/residence/me', body | dict(residence_area_id=None, version=1)).status_code == 422
    withdrawn = aoi.write('PUT', '/residence/me', body | dict(share_area_analytics=False, version=1)).json()
    assert withdrawn['version'] == 2 and not withdrawn['share_area_analytics']
    cleared = aoi.write('PUT', '/residence/me', dict(residence_area_id=None, share_area_analytics=False, version=2)).json()
    assert cleared['area'] is None and cleared['version'] == 3
    assert harness.client('forest').get('/residence/me').json()['area'] is None


def test_concurrent_profile_update_has_one_winner(harness):
    service = ResidenceService(harness.app.state.database)
    body = ResidenceUpdate(residence_area_id='27100', share_area_analytics=True, version=0)

    def update(_):
        from fastapi import HTTPException
        try:
            return service.me('u-aoi', body)['version']
        except HTTPException as error:
            return error.status_code

    with ThreadPoolExecutor(max_workers=2) as pool:
        assert sorted(pool.map(update, range(2))) == [1, 409]


def test_concurrent_registration_preserves_unique_account_and_consent(harness):
    service = ResidenceService(harness.app.state.database)

    def register(_):
        from fastapi import HTTPException
        try:
            service.register(Registration(**SIGNUP))
            return 201
        except HTTPException as error:
            return error.status_code

    with ThreadPoolExecutor(max_workers=2) as pool:
        assert sorted(pool.map(register, range(2))) == [201, 409]
    with harness.app.state.database.transaction() as conn:
        assert conn.execute('SELECT COUNT(*) FROM users WHERE username=?', (SIGNUP['username'],)).fetchone()[0] == 1
        assert conn.execute('SELECT COUNT(*) FROM residence_profiles WHERE share_analytics=1').fetchone()[0] == 0


def test_schema11_preserves_existing_data_and_rolls_back_failed_migration(harness, monkeypatch):
    db = harness.app.state.database
    with db.transaction(True) as conn:
        original = [tuple(row) for row in conn.execute('SELECT * FROM users ORDER BY id')]
        conn.execute('DROP TABLE residence_profiles')
        conn.execute('PRAGMA user_version=10')
    ddl = schema.DDL
    monkeypatch.setattr(schema, 'DDL', 'CREATE TABLE users(id TEXT)')
    import sqlite3
    with pytest.raises(sqlite3.OperationalError):
        schema.migrate(db)
    with db.transaction() as conn:
        assert conn.execute('PRAGMA user_version').fetchone()[0] == 10
        assert original == [tuple(row) for row in conn.execute('SELECT * FROM users ORDER BY id')]
    monkeypatch.setattr(schema, 'DDL', ddl)
    schema.migrate(db)
    schema.migrate(db)
    with db.transaction() as conn:
        assert conn.execute('PRAGMA user_version').fetchone()[0] == 11
        assert original == [tuple(row) for row in conn.execute('SELECT * FROM users ORDER BY id')]
        assert conn.execute('SELECT COUNT(*) FROM residence_profiles').fetchone()[0] == 0
        assert conn.execute('PRAGMA foreign_key_check').fetchall() == []


def test_origins_only_consented_confirmed_users_and_small_cities_are_omitted(analytics):
    outing(analytics, 'current', users=tuple(range(12)))
    profiles(analytics, range(5), '27100')
    profiles(analytics, range(5, 8), '27140')
    profiles(analytics, [8, 9], '26100', share=False)
    data = result(analytics)['origins']
    assert (data['total_visitors'], data['consented_visitors'], data['missing_visitors'], data['withheld_visitors'], data['suppressed_visitors']) == (12, 8, 2, 2, 3)
    assert [row['id'] for row in data['areas']] == ['27100']
    assert data['areas'][0]['visitors'] == 5 and data['areas'][0]['returning_visitors'] == 0
    assert data['areas'][0]['visits'] == 5
    serialized = json.dumps(data, ensure_ascii=False)
    assert '27140' not in serialized and '堺市' not in serialized and 'analytics-' not in serialized


def test_returning_users_need_earlier_same_provider_confirmed_visits(analytics):
    profiles(analytics, range(10))
    outing(analytics, 'current', users=tuple(range(10)))
    outing(analytics, 'old', users=tuple(range(5)), ended=(NOW - timedelta(days=400)).isoformat())
    outing(analytics, 'foreign', users=(5, 6), provider='shore-school', ended=(NOW - timedelta(days=500)).isoformat())
    data = result(analytics)['origins']['areas'][0]
    assert (data['visitors'], data['returning_visitors'], data['visits']) == (10, 5, 10)
    assert data['returning_status'] == 'available'


def test_small_returning_and_complementary_groups_hide_the_entire_city(analytics):
    profiles(analytics, range(6))
    outing(analytics, 'current', users=tuple(range(6)))
    outing(analytics, 'repeat', users=(0, 1), ended=(NOW - timedelta(days=2)).isoformat())
    data = result(analytics)['origins']
    assert data['areas'] == [] and data['suppressed_visitors'] == 6
    # Five returning visitors plus one first-time visitor must be suppressed too.
    outing(analytics, 'older', users=tuple(range(5)), ended=(NOW - timedelta(days=3)).isoformat())
    data = result(analytics)['origins']
    assert data['areas'] == [] and data['suppressed_visitors'] == 6


def test_withdrawal_immediately_removes_city_and_future_or_cancelled_are_not_origins(analytics):
    profiles(analytics, range(5))
    outing(analytics, 'current', users=tuple(range(5)))
    outing(analytics, 'future', users=(5, 6), ended=(NOW + timedelta(days=1)).isoformat())
    outing(analytics, 'cancelled', users=(7, 8), status='cancelled')
    assert result(analytics)['origins']['areas'][0]['visitors'] == 5
    ResidenceService(analytics.app.state.database).me('analytics-0', ResidenceUpdate(
        residence_area_id='27100', share_area_analytics=False, version=1))
    data = result(analytics)['origins']
    assert data['total_visitors'] == 5 and data['areas'] == []
    assert data['withheld_visitors'] == 1 and data['suppressed_visitors'] == 4
    assert data['status'] == 'insufficient_sample'


def test_no_visit_origins_are_empty_even_with_consented_profiles(analytics):
    profiles(analytics, range(5))
    data = result(analytics)['origins']
    assert data['total_visitors'] == data['consented_visitors'] == 0
    assert data['status'] == 'no_data' and data['areas'] == []
