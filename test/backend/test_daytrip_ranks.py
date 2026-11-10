"""R2 rank policy and real API discount boundaries, with isolated historical data."""
import json
from concurrent.futures import ThreadPoolExecutor
from datetime import UTC, datetime, timedelta

import pytest
from app.daytrip.ranks import NAMES, THRESHOLDS, evaluate, evidence_status, rank
from app.daytrip.service import Daytrip
from fastapi import HTTPException
from test_daytrip import accept_all, action, benefit, checked, create, finish
from test_daytrip import trip as trip


@pytest.mark.parametrize('level,threshold', list(enumerate(THRESHOLDS, 1)))
def test_all_ten_thresholds_and_guaranteed_lower_ranks(level, threshold):
    at = datetime(2027, 1, 2, tzinfo=UTC)
    current = evaluate(threshold, [(at, threshold)], at)
    assert current['rank'] == level and current['name'] == NAMES[level - 1]
    assert current['guaranteed_rank'] == min(level, 4)
    assert rank(threshold, 0) == min(level, 4)
    if threshold:
        assert rank(threshold - 1) == level - 1


def test_exact_365_days_and_timezone_boundary_preserve_lifetime():
    ended = datetime.fromisoformat('2026-01-03T18:00:00+09:00')
    expires = ended + timedelta(days=365)
    just_before = evaluate(1500, [(ended, 1500)], expires - timedelta(microseconds=1))
    assert just_before['rank'] == 5 and datetime.fromisoformat(just_before['next_demotion_at']) == expires
    exact = evaluate(1500, [(ended, 1500)], expires.astimezone(UTC))
    assert exact['rank'] == 4 and exact['recent_points'] == 0
    assert exact['lifetime_points'] == 1500 and exact['next_demotion_at'] is None
    assert exact['next_lifetime_points_needed'] == 0 and exact['next_recent_points_needed'] == 1500


def test_multi_step_demotion_and_future_activity_exclusion():
    at = datetime(2027, 1, 2, tzinfo=UTC)
    activities = [(at - timedelta(days=364), 5000), (at - timedelta(days=30), 4000)]
    top = evaluate(13000, activities, at)
    assert top['rank'] == 9 and top['lifetime_rank'] == 10
    assert datetime.fromisoformat(top['next_demotion_at']) == at + timedelta(days=1)
    assert evaluate(13000, activities, at + timedelta(days=1))['rank'] == 7
    inactive = evaluate(13000, activities, at + timedelta(days=366))
    assert inactive['rank'] == 4 and inactive['lifetime_points'] == 13000
    assert evaluate(1500, [(at + timedelta(days=1), 1500)], at)['rank'] == 4


def test_snapshot_does_not_accept_later_positive_credit_in_the_same_outing():
    at = datetime(2027, 1, 2, tzinfo=UTC)
    evidence = [dict(outing_id='past',ended_at=at.isoformat(),eligible_points=1500,ledger_ids=['original'])]
    later = [dict(id='original',outing_id='past',eligible_points=1500),
             dict(id='new-positive',outing_id='past',eligible_points=1500),
             dict(id='correction',outing_id='past',eligible_points=-1500)]
    remaining = evidence_status(evidence, later, at)
    assert remaining['rank'] == 1 and remaining['lifetime_points'] == remaining['recent_points'] == 0


def historical_credit(trip, total=1500, oldest_age=364, verified=True):
    """Seed 100-point partial attendances on separate days; award APIs are covered separately."""
    assert total % 100 == 0
    base = finish(trip, accept_all(trip, create(trip)), verify=verified)
    base_end = datetime.fromisoformat(base['ends_at'])
    recorded_at = datetime.now(UTC).isoformat()
    with trip['harness'].app.state.database.transaction(True) as conn:
        # These are isolated fixture rows, never the running application's data.
        first_end = base_end - timedelta(days=oldest_age)
        conn.execute('UPDATE daytrip_outings SET starts_at=?,ends_at=?,day=? WHERE id=?', ((first_end - timedelta(hours=9)).isoformat(),first_end.isoformat(),first_end.date().isoformat(),base['id']))
        conn.execute('UPDATE daytrip_participants SET points=100,full_route=0 WHERE outing_id=? AND user_id=?', (base['id'],'u-aoi'))
        conn.execute("UPDATE daytrip_ledger SET points=100 WHERE outing_id=? AND user_id='u-aoi' AND kind='award'", (base['id'],))
        conn.execute("UPDATE daytrip_ledger SET eligible_points=100 WHERE outing_id=? AND user_id='u-aoi' AND kind='verify'", (base['id'],))
        conn.execute("UPDATE daytrip_daily_awards SET day=? WHERE outing_id=? AND user_id='u-aoi'", (first_end.date().isoformat(),base['id']))
        for index in range(1, total // 100):
            oid = f'rank-history-{index}'
            ended = first_end + timedelta(days=index)
            conn.execute("INSERT INTO daytrip_outings(id,circle_id,title,route_json,starts_at,ends_at,day,status,leader_id,leader_accepted,plan_id,provider_id,invitation_id,plan_json,created_by,created_at) SELECT ?,circle_id,title,route_json,?,?,?,'confirmed',leader_id,leader_accepted,plan_id,provider_id,invitation_id,plan_json,created_by,created_at FROM daytrip_outings WHERE id=?", (oid,(ended - timedelta(hours=9)).isoformat(),ended.isoformat(),ended.date().isoformat(),base['id']))
            conn.execute("INSERT INTO daytrip_participants(outing_id,user_id,accepted,claimed,full_route,confirmed_by,provider_verified,points) VALUES(?,'u-aoi',1,1,0,'u-ren',?,100)", (oid,int(verified)))
            conn.execute("INSERT INTO daytrip_daily_awards VALUES('u-aoi',?,?)", (ended.date().isoformat(),oid))
            conn.execute("INSERT INTO daytrip_ledger VALUES(?,?,'u-aoi','award',100,0,'過去参加','D1',?)", ('award-' + oid,oid,recorded_at))
            if verified:
                conn.execute("INSERT INTO daytrip_ledger VALUES(?,?,'u-aoi','verify',0,100,'過去利用確認','D1',?)", ('verify-' + oid,oid,recorded_at))
    return base


def reserve(trip, reward, outing, key='rank-hold'):
    return checked(trip['aoi'].write('POST', '/daytrip/benefits/' + reward['id'] + '/reserve', dict(outing_id=outing['id'], client_request_id=key)))


def old_hold_snapshot(trip, rid):
    with trip['harness'].app.state.database.transaction(True) as conn:
        snapshot = json.loads(conn.execute('SELECT conditions_json FROM daytrip_redemptions WHERE id=?', (rid,)).fetchone()[0])
        snapshot.pop('rank_qualification')
        snapshot.pop('rank_evidence')
        snapshot['benefit'].pop('rank_policy_version')
        snapshot['benefit'].pop('original_rank_policy')
        snapshot['benefit']['min_rank'] = 4
        conn.execute('UPDATE daytrip_redemptions SET conditions_json=? WHERE id=?', (json.dumps(snapshot),rid))


def test_api_demotion_is_read_only_and_keeps_ledger_existing_users_and_media(trip):
    historical_credit(trip)
    db = trip['harness'].app.state.database
    with db.transaction() as conn:
        before = {table: [tuple(row) for row in conn.execute('SELECT * FROM ' + table + ' ORDER BY rowid')] for table in ('users','media','daytrip_ledger','daytrip_participants','settings')}
        version = conn.execute('PRAGMA user_version').fetchone()[0]
    first = checked(trip['aoi'].get('/daytrip/me'))
    assert first['rank'] == first['eligible_rank'] == 5
    trip['clock'][0] = datetime.fromisoformat(first['rank_status']['next_demotion_at'])
    later = checked(trip['aoi'].get('/daytrip/me'))
    assert later['rank'] == later['eligible_rank'] == 4
    assert later['points'] == first['points'] == 1500
    assert later['rank_status']['recent_points'] == 1400
    with db.transaction() as conn:
        assert conn.execute('PRAGMA user_version').fetchone()[0] == version
        for table, rows in before.items():
            assert [tuple(row) for row in conn.execute('SELECT * FROM ' + table + ' ORDER BY rowid')] == rows


def test_old_correction_is_attributed_to_original_activity_not_today(trip):
    old = finish(trip, accept_all(trip, create(trip)))
    newer = finish(trip, accept_all(trip, create(trip, day=3)))
    with trip['harness'].app.state.database.transaction(True) as conn:
        old_end = datetime.fromisoformat(old['ends_at']) - timedelta(days=400)
        conn.execute('UPDATE daytrip_outings SET ends_at=? WHERE id=?', (old_end.isoformat(),old['id']))
    before = checked(trip['aoi'].get('/daytrip/me'))
    newer_points = next(item['points'] for item in newer['participants'] if item['user_id'] == 'u-aoi')
    assert before['rank_status']['recent_points'] == newer_points
    action(trip, trip['aoi'], old, 'cancel', reason='過去の実施記録を訂正')
    after = checked(trip['aoi'].get('/daytrip/me'))
    assert after['rank_status']['recent_points'] == before['rank_status']['recent_points']
    assert after['points'] == after['eligible_points'] == newer_points


def test_late_provider_confirmation_does_not_restart_activity_window(trip):
    historical_credit(trip, verified=False)
    trip['clock'][0] += timedelta(days=400)
    before = checked(trip['aoi'].get('/daytrip/me'))
    assert before['rank'] == 4 and before['eligible_rank'] == 1
    with trip['harness'].app.state.database.transaction(True) as conn:
        # Confirming now records eligible credit, but the outing dates stay old.
        conn.execute("INSERT INTO daytrip_ledger SELECT 'late-' || id,outing_id,user_id,'verify',0,points,'遅い利用確認','D1',? FROM daytrip_ledger WHERE user_id='u-aoi' AND kind='award'", (trip['clock'][0].isoformat(),))
    after = checked(trip['aoi'].get('/daytrip/me'))
    assert after['eligible_points'] == 1500 and after['eligible_rank'] == 4
    assert after['eligible_rank_status']['recent_points'] == 0


def test_self_reported_rank_does_not_satisfy_provider_rank(trip):
    historical_credit(trip, verified=False)
    me = checked(trip['aoi'].get('/daytrip/me'))
    assert me['rank'] == 5 and me['eligible_rank'] == 1
    reward = benefit(trip, min_rank=5)
    future = accept_all(trip, create(trip, day=5))
    response = trip['aoi'].write('POST','/daytrip/benefits/' + reward['id'] + '/reserve',dict(outing_id=future['id'],client_request_id='not-qualified'))
    assert response.status_code == 409


@pytest.mark.parametrize('old_level,new_level', [(1,1),(2,3),(3,4),(4,5)])
def test_old_benefits_keep_their_point_threshold_without_row_migration(trip, old_level, new_level):
    item = benefit(trip, min_rank=old_level)
    with trip['harness'].app.state.database.transaction(True) as conn:
        conn.execute('DELETE FROM settings WHERE key=?', ('daytrip-benefit-rank:' + item['id'],))
        before = tuple(conn.execute('SELECT * FROM daytrip_benefits WHERE id=?', (item['id'],)).fetchone())
    visible = next(row for row in checked(trip['forest'].get('/daytrip/provider'))['benefits'] if row['id'] == item['id'])
    assert visible['min_rank'] == new_level and visible['original_rank_policy'] == 'D1'
    with trip['harness'].app.state.database.transaction() as conn:
        assert tuple(conn.execute('SELECT * FROM daytrip_benefits WHERE id=?', (item['id'],)).fetchone()) == before


def test_new_benefit_allows_top_rank_and_limits_input(trip):
    top = benefit(trip, min_rank=10)
    assert top['min_rank'] == 10 and top['rank_policy_version'] == top['original_rank_policy'] == 'R2'
    body = dict(plan_id='forest-day',title='範囲外',min_rank=11,discount_type='amount',discount_value=100,max_discount_yen=100,max_redemptions=1,starts_on='2027-01-01',ends_on='2027-02-01')
    assert trip['forest'].write('POST','/daytrip/benefits',body).status_code == 422


def test_old_client_min_rank_keeps_its_original_1500_point_condition(trip):
    body = dict(plan_id='forest-day',title='従来の四段条件',min_rank=4,discount_type='amount',discount_value=100,max_discount_yen=100,max_redemptions=1,starts_on='2027-01-01',ends_on='2027-02-01')
    saved = checked(trip['forest'].write('POST','/daytrip/benefits',body))
    assert saved['min_rank'] == 5 and saved['rank_policy_version'] == 'R2'
    assert trip['forest'].write('POST','/daytrip/benefits',body | {'min_rank': 5}).status_code == 422


@pytest.mark.parametrize('legacy', [False, True])
def test_reserved_price_and_use_survive_natural_demotion_but_new_holds_do_not(trip, legacy):
    historical_credit(trip)
    reward = benefit(trip, min_rank=4 if legacy else 5)
    if legacy:
        with trip['harness'].app.state.database.transaction(True) as conn:
            conn.execute('DELETE FROM settings WHERE key=?', ('daytrip-benefit-rank:' + reward['id'],))
    future = accept_all(trip, create(trip, day=5))
    held = reserve(trip, reward, future)
    with trip['harness'].app.state.database.transaction() as conn:
        snapshot = json.loads(conn.execute('SELECT conditions_json FROM daytrip_redemptions WHERE id=?', (held['id'],)).fetchone()[0])
        assert snapshot['rank_qualification']['rank'] == 5
    if legacy:
        # Old holds have price snapshots but no R2 qualification metadata.
        old_hold_snapshot(trip, held['id'])
    finish(trip, future)
    me = checked(trip['aoi'].get('/daytrip/me'))
    assert me['eligible_rank'] == 4
    kept = next(row for row in me['redemptions'] if row['id'] == held['id'])
    assert kept == held
    later = accept_all(trip, create(trip, day=6))
    denied = trip['aoi'].write('POST','/daytrip/benefits/' + reward['id'] + '/reserve',dict(outing_id=later['id'],client_request_id='after-demotion'))
    assert denied.status_code == 409
    used = checked(trip['forest'].write('POST','/daytrip/redemptions/' + held['id'] + '/redeem',dict(version=1)))
    assert used['status'] == 'redeemed'
    assert (used['original_yen'],used['discount_yen'],used['total_yen']) == (6000,300,5700)


def test_evidence_correction_cancels_unearned_hold_without_rewriting_price(trip):
    first = historical_credit(trip)
    reward = benefit(trip, min_rank=5)
    future = accept_all(trip, create(trip, day=5))
    held = reserve(trip, reward, future)
    action(trip, trip['aoi'], first, 'participants/u-aoi/cancel', reason='実参加の記録を訂正')
    me = checked(trip['aoi'].get('/daytrip/me'))
    assert me['points'] == 1400 and me['eligible_rank'] == 4
    cancelled = next(row for row in me['redemptions'] if row['id'] == held['id'])
    assert cancelled['status'] == 'cancelled' and cancelled['total_yen'] == held['total_yen']


def test_parallel_redemption_after_demotion_is_used_only_once(trip):
    historical_credit(trip)
    reward = benefit(trip, min_rank=5)
    future = accept_all(trip, create(trip, day=5))
    held = reserve(trip, reward, future)
    finish(trip, future)
    service = Daytrip(trip['harness'].app.state.database)

    def redeem_once(_):
        try:
            return service.redemption('provider-forest',held['id'],1)['status']
        except HTTPException as exc:
            return exc.status_code

    with ThreadPoolExecutor(max_workers=2) as pool:
        results = list(pool.map(redeem_once, range(2)))
    assert sorted(map(str,results)) == ['409','redeemed']


def test_natural_demotion_then_unrelated_old_correction_preserves_hold(trip):
    old = historical_credit(trip, total=1600, oldest_age=365)
    reward = benefit(trip, min_rank=5)
    future = accept_all(trip, create(trip, day=5))
    held = reserve(trip, reward, future)
    finish(trip, future)
    assert checked(trip['aoi'].get('/daytrip/me'))['eligible_rank'] == 4
    action(trip, trip['aoi'], old, 'participants/u-aoi/cancel', reason='確保時の年間活動に含まれない古い記録を訂正')
    kept = next(row for row in checked(trip['aoi'].get('/daytrip/me'))['redemptions'] if row['id'] == held['id'])
    assert kept == held
    used = checked(trip['forest'].write('POST','/daytrip/redemptions/' + held['id'] + '/redeem',dict(version=1)))
    assert used['status'] == 'redeemed' and used['total_yen'] == held['total_yen']
    assert not used['adjustment_required']


@pytest.mark.parametrize('legacy', [False, True])
def test_later_positive_activity_cannot_replace_corrected_held_evidence(trip, legacy):
    original = historical_credit(trip, oldest_age=14)
    reward = benefit(trip, min_rank=5)
    future = accept_all(trip, create(trip, day=6))
    held = reserve(trip, reward, future)
    if legacy:
        old_hold_snapshot(trip, held['id'])
    finish(trip, accept_all(trip, create(trip, day=3)))
    action(trip, trip['aoi'], original, 'participants/u-aoi/cancel', reason='確保時に根拠とした参加を訂正')
    me = checked(trip['aoi'].get('/daytrip/me'))
    assert me['eligible_points'] >= 1500 and me['eligible_rank'] == 5
    corrected = next(row for row in me['redemptions'] if row['id'] == held['id'])
    assert corrected['status'] == 'cancelled' and corrected['total_yen'] == held['total_yen']


def test_correction_racing_redemption_preserves_price_and_records_one_outcome(trip):
    original = historical_credit(trip, oldest_age=14)
    reward = benefit(trip, min_rank=5)
    future = accept_all(trip, create(trip, day=5))
    held = reserve(trip, reward, future)
    finish(trip, future)
    service = Daytrip(trip['harness'].app.state.database)
    current = checked(trip['aoi'].get('/daytrip/outings/' + original['id']))

    def operate(kind):
        try:
            if kind == 'correct':
                service.cancel('u-aoi',original['id'],dict(version=current['version'],reason='根拠を訂正'),participant_id='u-aoi')
                return 'corrected'
            return service.redemption('provider-forest',held['id'],1)['status']
        except HTTPException as exc:
            return exc.status_code

    with ThreadPoolExecutor(max_workers=2) as pool:
        results = list(pool.map(operate, ('correct','redeem')))
    assert results[0] == 'corrected' and results[1] in (409,'redeemed')
    record = next(row for row in checked(trip['aoi'].get('/daytrip/me'))['redemptions'] if row['id'] == held['id'])
    assert record['status'] == ('cancelled' if results[1] == 409 else 'redeemed')
    assert record['adjustment_required'] == (record['status'] == 'redeemed')
    assert (record['original_yen'],record['discount_yen'],record['total_yen']) == (6000,300,5700)
