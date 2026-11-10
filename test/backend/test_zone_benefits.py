"""Money, privacy, and concurrent budget boundaries through saved APIs."""
import json
from concurrent.futures import ThreadPoolExecutor
from datetime import UTC, datetime

import pytest
from app.daytrip import zone_benefits
from app.daytrip.service import Daytrip
from app.enrichment import enrich
from app.operational_seed import apply as apply_operating
from app.zone_benefit_seed import BENEFIT_ID
from app.zone_benefit_seed import apply as apply_zone_seed
from fastapi import HTTPException
from test_daytrip import accept_all, benefit, checked, create, finish
from test_daytrip import trip as trip
from test_operational_seed import fingerprint


def residence(client, area='27100', share=False):
    current = checked(client.get('/residence/me'))
    return checked(client.write('PUT', '/residence/me', dict(version=current['version'],
        residence_area_id=area, share_area_analytics=share)))


def configure(trip, reward, budget=600, additional=5):
    return checked(trip['forest'].write('PUT', '/daytrip/benefits/' + reward['id'] + '/zone-policy',
        dict(version=reward['version'], additional_percent=additional, budget_yen=budget)))


def offer(trip, reward, who='aoi'):
    rows = checked(trip[who].get('/daytrip/me'))['benefits']
    return next(row['zone_offer'] for row in rows if row['id'] == reward['id'])


def reserve(trip, reward, outing, who='aoi', key='zone-reserve'):
    return trip[who].write('POST', '/daytrip/benefits/' + reward['id'] + '/reserve',
        dict(outing_id=outing['id'], client_request_id=key))


def prepared(trip, budget=600):
    finish(trip, accept_all(trip, create(trip)))
    reward = benefit(trip)
    configure(trip, reward, budget)
    future = accept_all(trip, create(trip, day=3))
    residence(trip['aoi'])
    residence(trip['ren'])
    return reward, future


def test_reference_areas_and_analytics_consent_are_private_and_independent(trip):
    reward = benefit(trip)
    assert offer(trip, reward) is None
    configure(trip, reward, budget=10000)
    missing = offer(trip, reward)
    assert not missing['eligible'] and missing['effective_percent'] == 5
    assert missing['target_percent'] == 10 and missing['one_way_km'] is None
    for area, distance in zone_benefits.AREA_DISTANCES.items():
        residence(trip['aoi'], area, share=False)
        private = offer(trip, reward)
        assert private['eligible'] and private['one_way_km'] == distance
        assert private['effective_percent'] == 10 and private['discount_yen'] == 600
        residence(trip['aoi'], area, share=True)
        assert offer(trip, reward) == private
    residence(trip['aoi'], '13104', share=False)
    unknown = offer(trip, reward)
    assert not unknown['eligible'] and unknown['discount_yen'] == 300
    assert offer(trip, reward, 'ren')['one_way_km'] is None
    provider = checked(trip['forest'].get('/daytrip/provider'))
    item = next(row for row in provider['benefits'] if row['id'] == reward['id'])
    assert item['zone_policy_configurable'] and item['zone_policy']['remaining_yen'] == 10000
    assert 'zone_offer' not in item and 'area_id' not in json.dumps(item)


def test_zone_budget_cancel_and_saved_price_survive_residence_and_policy_change(trip):
    reward, future = prepared(trip)
    saved = checked(reserve(trip, reward, future))
    assert (saved['original_yen'], saved['discount_yen'], saved['total_yen']) == (6000, 600, 5400)
    assert checked(reserve(trip, reward, future))['id'] == saved['id']
    assert reserve(trip, reward, future, 'ren', 'other').status_code == 409
    assert not offer(trip, reward)['can_reserve']
    residence(trip['aoi'], None)
    assert offer(trip, reward)['effective_percent'] == 5
    policy = configure(trip, reward | dict(version=2), budget=600, additional=0)
    assert policy['used_yen'] == 600
    bad = trip['forest'].write('PUT', '/daytrip/benefits/' + reward['id'] + '/zone-policy',
        dict(version=3, additional_percent=5, budget_yen=599))
    assert bad.status_code == 409
    rows = checked(trip['aoi'].get('/daytrip/me'))['redemptions']
    assert rows[0]['discount_yen'] == 600
    db = trip['harness'].app.state.database
    with db.transaction() as conn:
        snapshot = json.loads(conn.execute('SELECT conditions_json FROM daytrip_redemptions WHERE id=?', (saved['id'],)).fetchone()[0])
        assert snapshot['zone_offer']['effective_percent'] == 10
        assert snapshot['zone_offer']['one_way_km'] == 32
    cancelled = checked(trip['aoi'].write('POST', '/daytrip/redemptions/' + saved['id'] + '/cancel', dict(version=1)))
    assert cancelled['status'] == 'cancelled'
    second = checked(reserve(trip, reward, future, 'ren', 'after-release'))
    assert second['discount_yen'] == 300
    finish(trip, future)
    redeemed = checked(trip['forest'].write('POST', '/daytrip/redemptions/' + second['id'] + '/redeem', dict(version=1)))
    assert redeemed['status'] == 'redeemed' and redeemed['discount_yen'] == 300
    assert trip['ren'].write('POST', '/daytrip/redemptions/' + second['id'] + '/cancel', dict(version=2)).status_code == 409
    with db.transaction() as conn:
        assert zone_benefits.used_yen(conn, reward['id']) == 300


def test_concurrent_budget_and_duplicate_requests_are_atomic(trip):
    reward, future = prepared(trip)
    service = Daytrip(trip['harness'].app.state.database)

    def attempt(uid):
        try:
            return service.reserve(uid, reward['id'], dict(outing_id=future['id'], client_request_id='parallel-' + uid))
        except HTTPException as error:
            return error.status_code

    with ThreadPoolExecutor(max_workers=2) as pool:
        results = list(pool.map(attempt, ('u-aoi', 'u-ren')))
    assert sum(isinstance(row, dict) for row in results) == 1
    assert 409 in results
    winner = next(row for row in results if isinstance(row, dict))
    with ThreadPoolExecutor(max_workers=2) as pool:
        repeated = list(pool.map(attempt, (winner['user_id'], winner['user_id'])))
    assert all(row['id'] == winner['id'] for row in repeated)
    with trip['harness'].app.state.database.transaction() as conn:
        assert zone_benefits.used_yen(conn, reward['id']) == 600
        assert conn.execute('SELECT COUNT(*) FROM daytrip_redemptions WHERE benefit_id=?', (reward['id'],)).fetchone()[0] == 1


def test_staff_scope_csrf_validation_and_existing_spend_are_enforced(trip):
    finish(trip, accept_all(trip, create(trip)))
    reward = benefit(trip)
    future = accept_all(trip, create(trip, day=3))
    saved = checked(reserve(trip, reward, future))
    assert saved['discount_yen'] == 300  # No policy: existing calculation is unchanged.
    existing = next(row for row in checked(trip['forest'].get('/daytrip/provider'))['benefits'] if row['id'] == reward['id'])
    assert existing['zone_policy'] is None and existing['zone_used_yen'] == 300
    path = '/daytrip/benefits/' + reward['id'] + '/zone-policy'
    data = dict(version=1, additional_percent=5, budget_yen=300)
    for client in ('aoi', 'shore'):
        assert trip[client].write('PUT', path, data).status_code == 404
    assert trip['harness'].client().write('PUT', path, data).status_code == 401
    assert trip['forest'].write('PUT', path, data, headers={'X-CSRF-Token': 'wrong'}).status_code == 403
    for update in (dict(budget_yen=0), dict(additional_percent=101), dict(additional_percent=True), dict(user_id='u-ren')):
        assert trip['forest'].write('PUT', path, data | update).status_code == 422
    assert trip['forest'].write('PUT', path, data | dict(budget_yen=299)).status_code == 409
    state = checked(trip['forest'].write('PUT', path, data))
    assert state['used_yen'] == 300 and state['remaining_yen'] == 0
    assert trip['forest'].write('PUT', path, data).status_code == 409
    amount = benefit(trip, discount_type='amount', discount_value=500)
    assert trip['forest'].write('PUT', '/daytrip/benefits/' + amount['id'] + '/zone-policy', data).status_code == 409


@pytest.mark.parametrize('distance,eligible', [(19.99, False), (20, True), (40, True), (40.01, False)])
def test_inclusive_zone_and_discount_caps(trip, monkeypatch, distance, eligible):
    monkeypatch.setitem(zone_benefits.AREA_DISTANCES, '27100', distance)
    reward = benefit(trip, discount_value=90, max_discount_yen=5800)
    configure(trip, reward, budget=10000, additional=20)
    residence(trip['aoi'])
    value = offer(trip, reward)
    assert value['eligible'] is eligible
    assert value['effective_percent'] == (100 if eligible else 90)
    assert value['discount_yen'] == (5800 if eligible else 5400)


def test_explicit_zone_seed_is_append_only_and_repeatable(harness):
    at = datetime(2026, 11, 10, 3, tzinfo=UTC)
    db = harness.app.state.database
    enrich(db, harness.settings, at)
    apply_operating(db, harness.settings, at)
    before = fingerprint(db)
    report = apply_zone_seed(db, at)
    after = fingerprint(db)
    assert all(before[table] <= after[table] for table in before)
    assert report['benefit_id'] == BENEFIT_ID and report['prior_rows_updated'] == 0
    assert report['policy']['remaining_yen'] == 12000
    assert apply_zone_seed(db, at)['already_applied']
    assert fingerprint(db) == after
    with db.transaction() as conn:
        assert conn.execute('PRAGMA foreign_key_check').fetchall() == []
        assert conn.execute('SELECT COUNT(*) FROM daytrip_benefits WHERE id=?', (BENEFIT_ID,)).fetchone()[0] == 1
