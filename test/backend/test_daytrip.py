import json
import sqlite3
from concurrent.futures import ThreadPoolExecutor
from datetime import UTC, datetime, timedelta

import pytest
from fastapi import HTTPException

from app.daytrip import service as module
from app.daytrip.schema import migrate
from app.daytrip.service import Daytrip, rank, route_out
from test_circles import circle, requirements


@pytest.fixture
def trip(harness, monkeypatch):
    time = [datetime(2027, 1, 1, tzinfo=UTC)]
    monkeypatch.setattr(module, 'clock_now', lambda: time[0])
    aoi, ren, mio, forest, shore = [harness.client(name) for name in ('aoi','ren','mio','forest','shore')]
    group = circle(aoi, invitee_ids=['u-ren','u-mio'])
    for invitation, client in zip(group['invitations'], (ren,mio)):
        # Invitation order is not assumed by the public contract.
        client = ren if invitation['invitee']['id'] == 'u-ren' else mio
        checked(client.write('POST', '/circle-invitations/' + invitation['id'] + '/respond', dict(version=1,decision='accepted',client_request_id='accept-' + invitation['id'])))
    rid = module.ROUTES[0]['id']
    checked(forest.write('PUT', '/daytrip/plan-routes/forest-day', dict(route_id=rid)))
    requirements(aoi, group['id'], planned_people=3, nights=0, date_start='2027-01-02')
    current = checked(aoi.get('/circles/' + group['id']))
    invitation = checked(aoi.write('POST', '/circles/' + group['id'] + '/provider-invitations', dict(plan_id='forest-day',plan_version=1,requirements_version=current['requirements']['version'],share_note='日帰りの相談',sharing_confirmed=True,version=current['version'],client_request_id='day-provider')))
    checked(forest.write('POST', '/circle-provider-invitations/' + invitation['id'] + '/respond', dict(version=1,decision='accepted',client_request_id='provider-accept-day')))
    return dict(harness=harness, aoi=aoi, ren=ren, mio=mio, forest=forest, shore=shore, circle=group['id'], route=rid, clock=time)


def checked(response):
    assert response.status_code == 200, response.text
    return response.json()


def create(trip, day=2, **extra):
    data = dict(title='仲間の日帰り',route_id=trip['route'],starts_at=f'2027-01-{day:02d}T09:00:00+09:00',ends_at=f'2027-01-{day:02d}T18:00:00+09:00',participant_ids=['u-aoi','u-ren','u-mio'],leader_id='u-aoi',plan_id='forest-day',client_request_id=f'outing-{day}') | extra
    return checked(trip['aoi'].write('POST','/circles/' + trip['circle'] + '/outings',data))


def action(trip, client, outing, endpoint, **values):
    current = checked(trip['aoi'].get('/daytrip/outings/' + outing['id']))
    return checked(client.write('POST', '/daytrip/outings/' + outing['id'] + '/' + endpoint, dict(version=current['version']) | values))


def accept_all(trip, outing):
    for name in ('aoi','ren','mio'):
        outing = action(trip, trip[name], outing, 'accept', accept_leader=name == 'aoi')
    return outing


def finish(trip, outing, verify=True):
    trip['clock'][0] = datetime.fromisoformat(outing['ends_at']) + timedelta(minutes=1)
    for name in ('aoi','ren','mio'):
        outing = action(trip, trip[name], outing, 'claim', full_route=True)
    for witness, target in (('ren','aoi'),('mio','ren'),('aoi','mio')):
        outing = action(trip, trip[witness], outing, 'confirm', participant_id='u-' + target)
    if verify:
        outing = action(trip, trip['forest'], outing, 'provider-confirm', participant_ids=['u-aoi','u-ren','u-mio'])
    return outing


def benefit(trip, **extra):
    return checked(trip['forest'].write('POST','/daytrip/benefits',dict(plan_id='forest-day',title='次の開催の割引',min_rank=1,rank_policy_version='R2',discount_type='percent',discount_value=5,max_discount_yen=1000,max_redemptions=10,starts_on='2027-01-01',ends_on='2027-02-28') | extra))


def test_catalog_boundaries_auth_and_no_legacy_credit(trip):
    assert trip['harness'].client().get('/daytrip/catalog').status_code == 401
    catalog = checked(trip['aoi'].get('/daytrip/catalog'))
    assert catalog['routes'] and catalog['rules']['rank_thresholds'] == [0,100,300,800,1500,2500,4000,6000,9000,13000]
    assert catalog['rules']['rank_policy_version'] == 'R2'
    assert checked(trip['aoi'].get('/daytrip/me'))['points'] == 0
    for km, zone in ((19.99,'nearby'),(20,'target'),(40,'target'),(40.01,'outside'),(None,'unknown')):
        assert route_out(dict(one_way_km=km,one_way_minutes=30))['zone'] == zone
    assert route_out(dict(one_way_km=30,one_way_minutes=180))['zone'] == 'target'
    assert [rank(n) for n in (0,299,300,799,800,1499,1500)] == [1,2,3,3,4,4,5]


def test_predeparture_consent_and_future_award_rejected(trip):
    outing = create(trip)
    oid = outing['id']
    assert trip['ren'].write('POST',f'/daytrip/outings/{oid}/accept',dict(version=1,accept_leader=True)).status_code == 409
    assert trip['ren'].write('POST',f'/daytrip/outings/{oid}/claim',dict(version=1,full_route=True)).status_code == 409
    assert trip['aoi'].write('POST',f'/daytrip/outings/{oid}/accept',dict(version=1,accept_leader=True),headers={'X-CSRF-Token':'wrong'}).status_code == 403
    outing = accept_all(trip, outing)
    trip['clock'][0] = datetime.fromisoformat(outing['starts_at'])
    assert trip['aoi'].write('POST',f'/daytrip/outings/{oid}/leader',dict(version=outing['version'],leader_id='u-ren')).status_code == 409
    assert trip['mio'].write('POST',f'/daytrip/outings/{oid}/accept',dict(version=outing['version'],accept_leader=False)).status_code == 409
    assert checked(trip['aoi'].get('/daytrip/me'))['points'] == 0


def test_outing_validation_and_scope(trip):
    base = dict(title='一日',route_id=trip['route'],starts_at='2027-01-02T09:00:00+09:00',ends_at='2027-01-02T18:00:00+09:00',participant_ids=['u-aoi','u-ren'],leader_id='u-aoi',client_request_id='invalid')
    path = '/circles/' + trip['circle'] + '/outings'
    for changes, status in ((dict(route_id='unregistered'),404),(dict(ends_at='2027-01-03T01:00:00+09:00'),422),(dict(ends_at='2027-01-02T09:01:00+09:00'),422),(dict(starts_at='2026-12-01T09:00:00+09:00'),422),(dict(participant_ids=['u-aoi','provider-forest']),404)):
        assert trip['aoi'].write('POST',path,base | changes).status_code == status
    assert trip['ren'].write('POST',path,base).status_code == 404
    assert trip['shore'].write('PUT','/daytrip/plan-routes/forest-day',dict(route_id=trip['route'])).status_code == 404


def test_awards_provider_qualification_and_repeat_delivery(trip):
    outing = accept_all(trip, create(trip))
    outing = finish(trip, outing, verify=False)
    distance = int(min(module.ROUTES[0]['one_way_km'] * 2,200) // 10)
    aoi = checked(trip['aoi'].get('/daytrip/me'))
    assert aoi['points'] == 150 + distance and aoi['eligible_points'] == 0
    assert aoi['completed_count'] == aoi['leader_count'] == 1
    assert trip['shore'].write('POST','/daytrip/outings/' + outing['id'] + '/provider-confirm',dict(version=outing['version'],participant_ids=['u-aoi'])).status_code == 404
    outing = action(trip, trip['forest'], outing, 'provider-confirm', participant_ids=['u-aoi','u-ren','u-mio'])
    assert checked(trip['aoi'].get('/daytrip/me'))['eligible_points'] == aoi['points']
    outing = action(trip, trip['forest'], outing, 'provider-confirm', participant_ids=['u-aoi'])
    assert checked(trip['aoi'].get('/daytrip/me'))['eligible_points'] == aoi['points']
    assert trip['aoi'].write('POST','/daytrip/outings/' + outing['id'] + '/confirm',dict(version=outing['version'],participant_id='u-aoi')).status_code == 409


def test_nonprovider_points_never_unlock_benefit(trip):
    outing = finish(trip, accept_all(trip, create(trip, plan_id=None)), verify=False)
    reward = benefit(trip)
    future = accept_all(trip, create(trip, day=3))
    result = trip['aoi'].write('POST','/daytrip/benefits/' + reward['id'] + '/reserve',dict(outing_id=future['id'],client_request_id='reserve'))
    assert result.status_code == 409
    assert checked(trip['aoi'].get('/daytrip/me'))['points'] > 0
    assert checked(trip['aoi'].get('/daytrip/me'))['eligible_points'] == 0
    assert trip['forest'].write('POST','/daytrip/outings/' + outing['id'] + '/provider-confirm',dict(version=outing['version'],participant_ids=['u-aoi'])).status_code == 404


def test_discount_end_to_end_snapshot_and_duplicate_use(trip):
    finish(trip, accept_all(trip, create(trip)))
    reward = benefit(trip)
    future = accept_all(trip, create(trip, day=3))
    path = '/daytrip/benefits/' + reward['id'] + '/reserve'
    data = dict(outing_id=future['id'],client_request_id='reserve')
    saved = checked(trip['aoi'].write('POST',path,data))
    assert (saved['original_yen'],saved['discount_yen'],saved['total_yen']) == (6000,300,5700)
    assert checked(trip['aoi'].write('POST',path,data))['id'] == saved['id']
    assert trip['aoi'].write('POST',path,data | dict(client_request_id='reserve-again')).status_code == 409
    assert trip['forest'].write('POST','/daytrip/redemptions/' + saved['id'] + '/redeem',dict(version=1)).status_code == 409
    finish(trip, future)
    used = checked(trip['forest'].write('POST','/daytrip/redemptions/' + saved['id'] + '/redeem',dict(version=1)))
    assert used['status'] == 'redeemed'
    assert trip['forest'].write('POST','/daytrip/redemptions/' + saved['id'] + '/redeem',dict(version=used['version'])).status_code == 409
    assert trip['aoi'].write('POST','/daytrip/redemptions/' + saved['id'] + '/cancel',dict(version=used['version'])).status_code == 409


def test_changed_plan_and_closed_benefit_block_usage(trip):
    finish(trip, accept_all(trip, create(trip)))
    reward = benefit(trip)
    future = accept_all(trip, create(trip, day=3))
    saved = checked(trip['aoi'].write('POST','/daytrip/benefits/' + reward['id'] + '/reserve',dict(outing_id=future['id'],client_request_id='reserve')))
    finish(trip, future)
    with trip['harness'].app.state.database.transaction(True) as conn:
        conn.execute("UPDATE provider_plans SET version=version+1 WHERE id='forest-day'")
    assert trip['forest'].write('POST','/daytrip/redemptions/' + saved['id'] + '/redeem',dict(version=1)).status_code == 409
    assert checked(trip['aoi'].get('/daytrip/me'))['redemptions'][0]['original_yen'] == 6000
    checked(trip['forest'].write('POST','/daytrip/benefits/' + reward['id'] + '/close',dict(version=1)))
    assert checked(trip['aoi'].get('/daytrip/me'))['redemptions'][0]['status'] == 'cancelled'


def test_single_person_correction_withdraws_witness_then_reconfirms(trip):
    outing = finish(trip, accept_all(trip, create(trip)))
    # Ren witnessed Aoi; Aoi witnessed Mio. Cancelling Aoi invalidates only
    # Aoi's award and their testimony for Mio, not Ren's own attendance.
    before = checked(trip['ren'].get('/daytrip/me'))['points']
    outing = action(trip, trip['aoi'], outing, 'participants/u-aoi/cancel', reason='欠席だったため訂正')
    assert checked(trip['aoi'].get('/daytrip/me'))['points'] == 0
    assert checked(trip['ren'].get('/daytrip/me'))['points'] == before
    assert checked(trip['mio'].get('/daytrip/me'))['points'] == 0
    outing = action(trip, trip['ren'], outing, 'confirm', participant_id='u-mio')
    assert checked(trip['mio'].get('/daytrip/me'))['points'] == before
    assert checked(trip['mio'].get('/daytrip/me'))['eligible_points'] == 0
    outing = action(trip, trip['forest'], outing, 'provider-confirm', participant_ids=['u-mio'])
    result = checked(trip['mio'].get('/daytrip/me'))
    assert result['eligible_points'] == before
    assert sum(item['points'] for item in result['ledger']) == before
    assert trip['ren'].write('POST','/daytrip/outings/' + outing['id'] + '/confirm',dict(version=outing['version'],participant_id='u-aoi')).status_code == 409


def test_cancel_preserves_ledger_and_same_day_cap(trip):
    first = accept_all(trip, create(trip))
    second = accept_all(trip, create(trip,client_request_id='same-day-again'))
    first = finish(trip, first)
    first = action(trip,trip['aoi'],first,'cancel',reason='開催を取り消す')
    me = checked(trip['aoi'].get('/daytrip/me'))
    assert me['points'] == me['eligible_points'] == 0
    assert {'award','verify','reverse'} <= {item['kind'] for item in me['ledger']}
    for name in ('aoi','ren','mio'):
        second = action(trip,trip[name],second,'claim',full_route=True)
    assert trip['ren'].write('POST','/daytrip/outings/' + second['id'] + '/confirm',dict(version=second['version'],participant_id='u-aoi')).status_code == 409


def test_parallel_confirmation_only_awards_once(trip):
    outing = accept_all(trip,create(trip))
    trip['clock'][0] = datetime.fromisoformat(outing['ends_at'])
    for name in ('aoi','ren','mio'):
        outing = action(trip,trip[name],outing,'claim',full_route=True)
    service = Daytrip(trip['harness'].app.state.database)
    def confirm(witness):
        try:
            service.confirm(witness,outing['id'],dict(version=outing['version'],participant_id='u-aoi'))
            return 200
        except HTTPException as exc:
            return exc.status_code
    with ThreadPoolExecutor(max_workers=2) as pool:
        results = list(pool.map(confirm,('u-ren','u-mio')))
    assert sorted(results) == [200,409]
    assert len(checked(trip['aoi'].get('/daytrip/me'))['ledger']) == 1


def test_partial_participation_and_leader_change(trip):
    outing = create(trip)
    outing = action(trip,trip['aoi'],outing,'leader',leader_id='u-ren')
    for name in ('aoi','ren','mio'):
        outing = action(trip,trip[name],outing,'accept',accept_leader=name == 'ren')
    trip['clock'][0] = datetime.fromisoformat(outing['ends_at'])
    outing = action(trip,trip['ren'],outing,'claim',full_route=False)
    outing = action(trip,trip['aoi'],outing,'claim',full_route=True)
    action(trip,trip['aoi'],outing,'confirm',participant_id='u-ren')
    assert checked(trip['ren'].get('/daytrip/me'))['points'] == 100


def test_leave_rejoin_never_revives_old_participation(trip):
    outing = accept_all(trip,create(trip))
    db = trip['harness'].app.state.database
    with db.transaction(True) as conn:
        conn.execute("DELETE FROM travel_party_members WHERE party_id=? AND user_id='u-ren'",(trip['circle'],))
        conn.execute("INSERT INTO travel_party_members VALUES(?,'u-ren')",(trip['circle'],))
    outing = checked(trip['aoi'].get('/daytrip/outings/' + outing['id']))
    assert next(p for p in outing['participants'] if p['user_id'] == 'u-ren')['revoked'] == 1
    assert trip['ren'].write('POST','/daytrip/outings/' + outing['id'] + '/accept',dict(version=outing['version'])).status_code == 409


def test_restart_migration_is_idempotent_and_resume_keeps_data(trip):
    db = trip['harness'].app.state.database
    create(trip)
    existing = checked(trip['aoi'].get('/me/resume-state'))
    assert existing['page'] == 'daytrip'
    saved = checked(trip['aoi'].write('PUT','/me/resume-state',existing | dict(page='daytrip',community_id='peers',circle_id=trip['circle'])))
    with db.transaction() as conn:
        counts = [conn.execute('SELECT COUNT(*) FROM ' + table).fetchone()[0] for table in ('users','media','travel_parties','daytrip_outings')]
    db.initialize()
    from app.marketplace.schema import migrate as m2
    from app.journal.schema import migrate as m3
    from app.circles.schema import migrate as m4
    from app.circles.discovery_schema import migrate as m5
    from app.reflections.schema import migrate as m6
    from app.occasions.schema import migrate as m7
    from app.personalization.schema import migrate as m8
    for step in (m2,m3,m4,m5,m6,m7,m8,migrate,migrate):
        step(db)
    assert checked(trip['aoi'].get('/me/resume-state')) == saved
    with db.transaction() as conn:
        assert conn.execute('PRAGMA user_version').fetchone()[0] == 11
        assert not conn.execute('PRAGMA foreign_key_check').fetchall()
        assert [conn.execute('SELECT COUNT(*) FROM ' + table).fetchone()[0] for table in ('users','media','travel_parties','daytrip_outings')] == counts


def test_old_v8_migration_preserves_rows_and_rolls_back(tmp_path, monkeypatch):
    from app.database import Database
    from app.daytrip import schema as day_schema
    from app.marketplace.schema import migrate as m2
    from app.journal.schema import migrate as m3
    from app.circles.schema import migrate as m4
    from app.circles.discovery_schema import migrate as m5
    from app.reflections.schema import migrate as m6
    from app.occasions.schema import migrate as m7
    from app.personalization import schema as resume_schema
    db = Database(tmp_path / 'before.db')
    db.initialize()
    for step in (m2,m3,m4,m5,m6,m7):
        step(db)
    original_resume = resume_schema.DDL
    monkeypatch.setattr(resume_schema,'DDL',tuple(sql.replace(",'daytrip'",'') for sql in original_resume))
    resume_schema.migrate(db)
    monkeypatch.setattr(resume_schema,'DDL',original_resume)
    with db.transaction(True) as conn:
        conn.execute("INSERT INTO user_resume_state VALUES('u-aoi','journal','peers',NULL,?,3)",(resume_schema.DEFAULT_FILTERS,))
        conn.execute("INSERT INTO media VALUES('kept-photo','u-aoi','kept.jpg',10,10,'hash',0,'2026-01-01')")
        conn.execute("INSERT INTO journal_journeys VALUES('kept-journey','u-aoi','残す旅',1,'2026-01-01')")
        tables = [row[0] for row in conn.execute("SELECT name FROM sqlite_master WHERE type='table'")]
        before = {table:[tuple(row) for row in conn.execute('SELECT * FROM "' + table + '" ORDER BY rowid')] for table in tables}
        triggers = [tuple(row) for row in conn.execute("SELECT name,sql FROM sqlite_master WHERE type='trigger' AND name LIKE 'resume_%' ORDER BY name")]
    original = day_schema.DDL
    monkeypatch.setattr(day_schema,'DDL',original + ('INVALID SQL',))
    with pytest.raises(sqlite3.OperationalError):
        day_schema.migrate(db)
    with db.transaction() as conn:
        assert conn.execute('PRAGMA user_version').fetchone()[0] == 8
        assert not conn.execute("SELECT 1 FROM sqlite_master WHERE name='daytrip_outings'").fetchone()
    monkeypatch.setattr(day_schema,'DDL',original)
    day_schema.migrate(db)
    day_schema.migrate(db)
    with db.transaction() as conn:
        assert {table:[tuple(row) for row in conn.execute('SELECT * FROM "' + table + '" ORDER BY rowid')] for table in tables} == before
        assert [tuple(row) for row in conn.execute("SELECT name,sql FROM sqlite_master WHERE type='trigger' AND name LIKE 'resume_%' ORDER BY name")] == triggers
        assert not conn.execute('PRAGMA foreign_key_check').fetchall()
        assert Daytrip.balance(conn,'u-aoi')['points'] == 0
    with db.transaction(True) as conn:
        conn.execute("UPDATE user_resume_state SET page='daytrip' WHERE user_id='u-aoi'")


def test_parallel_benefit_limit_and_actor_scope(trip):
    finish(trip,accept_all(trip,create(trip)))
    reward = benefit(trip,max_redemptions=1)
    future = accept_all(trip,create(trip,day=3))
    service = Daytrip(trip['harness'].app.state.database)
    def reserve(uid):
        try:
            return service.reserve(uid,reward['id'],dict(outing_id=future['id'],client_request_id='reserve-' + uid))
        except HTTPException as exc:
            return exc.status_code
    with ThreadPoolExecutor(max_workers=2) as pool:
        results = list(pool.map(reserve,('u-aoi','u-ren')))
    assert sum(isinstance(item,dict) for item in results) == 1
    assert results.count(409) == 1
    saved = next(item for item in results if isinstance(item,dict))
    assert trip['shore'].write('POST','/daytrip/redemptions/' + saved['id'] + '/cancel',dict(version=1)).status_code == 404
    assert trip['aoi'].write('POST','/daytrip/benefits',dict(plan_id='forest-day',title='権限外',min_rank=1,discount_type='amount',discount_value=300,max_discount_yen=300,max_redemptions=10,starts_on='2027-01-01',ends_on='2027-01-30')).status_code == 404


def test_cancel_unused_plan_does_not_change_other_discount(trip):
    finish(trip,accept_all(trip,create(trip)))
    reward = benefit(trip)
    future = accept_all(trip,create(trip,day=3))
    saved = checked(trip['aoi'].write('POST','/daytrip/benefits/' + reward['id'] + '/reserve',dict(outing_id=future['id'],client_request_id='keep-reservation')))
    unrelated = create(trip,day=4)
    action(trip,trip['aoi'],unrelated,'cancel',reason='別の日の予定を中止')
    redemption = next(row for row in checked(trip['aoi'].get('/daytrip/me'))['redemptions'] if row['id'] == saved['id'])
    assert redemption['status'] == 'reserved' and redemption['adjustment_required'] == 0


def test_rank_downgrade_cancels_unused_benefit_and_keeps_used_price(trip):
    first = finish(trip,accept_all(trip,create(trip)))
    reward = benefit(trip)
    second = accept_all(trip,create(trip,day=3))
    first_discount = checked(trip['aoi'].write('POST','/daytrip/benefits/' + reward['id'] + '/reserve',dict(outing_id=second['id'],client_request_id='first-discount')))
    finish(trip,second)
    used = checked(trip['forest'].write('POST','/daytrip/redemptions/' + first_discount['id'] + '/redeem',dict(version=1)))
    third = accept_all(trip,create(trip,day=4))
    second_discount = checked(trip['aoi'].write('POST','/daytrip/benefits/' + reward['id'] + '/reserve',dict(outing_id=third['id'],client_request_id='second-discount')))
    action(trip,trip['aoi'],first,'cancel',reason='初回実績の訂正')
    action(trip,trip['aoi'],second,'cancel',reason='二回目実績の訂正')
    me = checked(trip['aoi'].get('/daytrip/me'))
    assert me['points'] == me['eligible_points'] == 0
    records = {row['id']:row for row in me['redemptions']}
    assert records[used['id']]['status'] == 'redeemed'
    assert records[used['id']]['total_yen'] == used['total_yen']
    assert records[used['id']]['adjustment_required'] == 1
    assert records[second_discount['id']]['status'] == 'cancelled'


def test_dated_plan_full_time_and_capacity_must_fit(trip):
    with trip['harness'].app.state.database.transaction(True) as conn:
        body = json.loads(conn.execute("SELECT body FROM provider_plans WHERE id='forest-day'").fetchone()[0])
        body.update(schedule_type='dated',starts_at='2027-01-02T13:00:00+09:00',ends_at='2027-01-02T15:00:00+09:00')
        conn.execute("UPDATE provider_plans SET body=? WHERE id='forest-day'",(json.dumps(body),))
    data = dict(title='日帰り',route_id=trip['route'],starts_at='2027-01-02T09:00:00+09:00',ends_at='2027-01-02T12:00:00+09:00',participant_ids=['u-aoi','u-ren','u-mio'],leader_id='u-aoi',plan_id='forest-day',client_request_id='too-early-return')
    assert trip['aoi'].write('POST','/circles/' + trip['circle'] + '/outings',data).status_code == 422
    checked(trip['aoi'].write('POST','/circles/' + trip['circle'] + '/outings',data | dict(ends_at='2027-01-02T18:00:00+09:00')))
    with trip['harness'].app.state.database.transaction(True) as conn:
        body['max_people'] = 2
        conn.execute("UPDATE provider_plans SET body=? WHERE id='forest-day'",(json.dumps(body),))
    assert trip['aoi'].write('POST','/circles/' + trip['circle'] + '/outings',data | dict(ends_at='2027-01-02T18:00:00+09:00',client_request_id='too-many')).status_code == 422


def test_leader_cancels_before_departure_requires_new_acceptance(trip):
    outing = accept_all(trip,create(trip))
    outing = action(trip,trip['aoi'],outing,'participants/u-aoi/cancel',reason='予定変更で欠席')
    assert outing['leader_accepted'] is False
    assert outing['status'] == 'scheduled'
    outing = action(trip,trip['aoi'],outing,'leader',leader_id='u-ren')
    assert outing['leader_accepted'] is False
    outing = action(trip,trip['ren'],outing,'accept',accept_leader=True)
    assert outing['leader_accepted'] is True


def reservation(trip, client, reward, outing, key):
    return checked(client.write('POST','/daytrip/benefits/' + reward['id'] + '/reserve',dict(outing_id=outing['id'],client_request_id=key)))


@pytest.mark.parametrize('loss', ['circle_leave','community_leave','account_disabled'])
def test_revocation_releases_only_own_unused_holds_and_restores_capacity(trip, loss):
    finish(trip,accept_all(trip,create(trip)))
    reward = benefit(trip,max_redemptions=3)
    used_outing = accept_all(trip,create(trip,day=3))
    used = reservation(trip,trip['ren'],reward,used_outing,'used')
    finish(trip,used_outing)
    used = checked(trip['forest'].write('POST','/daytrip/redemptions/' + used['id'] + '/redeem',dict(version=1)))
    future = accept_all(trip,create(trip,day=4))
    own = reservation(trip,trip['ren'],reward,future,'own-unused')
    other = reservation(trip,trip['aoi'],reward,future,'other-unused')
    db = trip['harness'].app.state.database
    with db.transaction() as conn:
        used_before = tuple(conn.execute('SELECT * FROM daytrip_redemptions WHERE id=?',(used['id'],)).fetchone())
        other_before = tuple(conn.execute('SELECT * FROM daytrip_redemptions WHERE id=?',(other['id'],)).fetchone())
        ledger_before = [tuple(row) for row in conn.execute('SELECT * FROM daytrip_ledger ORDER BY id')]
    if loss == 'circle_leave':
        current = checked(trip['ren'].get('/circles/' + trip['circle']))
        checked(trip['ren'].write('POST','/circles/' + trip['circle'] + '/leave',dict(version=current['version'])))
    elif loss == 'community_leave':
        checked(trip['ren'].write('POST','/communities/peers/leave'))
    else:
        with db.transaction(True) as conn:
            conn.execute("UPDATE users SET login_enabled=0 WHERE id='u-ren'")
    with db.transaction() as conn:
        assert conn.execute('SELECT status FROM daytrip_redemptions WHERE id=?',(own['id'],)).fetchone()[0] == 'cancelled'
        assert tuple(conn.execute('SELECT * FROM daytrip_redemptions WHERE id=?',(used['id'],)).fetchone()) == used_before
        assert tuple(conn.execute('SELECT * FROM daytrip_redemptions WHERE id=?',(other['id'],)).fetchone()) == other_before
        assert [tuple(row) for row in conn.execute('SELECT * FROM daytrip_ledger ORDER BY id')] == ledger_before
    # Three slots: one used, one retained, and the released slot can be used by Mio.
    replacement = reservation(trip,trip['mio'],reward,future,'replacement')
    assert replacement['status'] == 'reserved'


@pytest.mark.parametrize('close_target', ['circle','provider_invitation'])
def test_closed_sharing_releases_pending_holds_but_keeps_consumed_record(trip, close_target):
    finish(trip,accept_all(trip,create(trip)))
    reward = benefit(trip)
    used_outing = accept_all(trip,create(trip,day=3))
    used = reservation(trip,trip['aoi'],reward,used_outing,'use-before-close')
    finish(trip,used_outing)
    used = checked(trip['forest'].write('POST','/daytrip/redemptions/' + used['id'] + '/redeem',dict(version=1)))
    future = accept_all(trip,create(trip,day=4))
    reserved = reservation(trip,trip['aoi'],reward,future,'close-pending')
    db = trip['harness'].app.state.database
    with db.transaction() as conn:
        used_before = tuple(conn.execute('SELECT * FROM daytrip_redemptions WHERE id=?',(used['id'],)).fetchone())
    current = checked(trip['aoi'].get('/circles/' + trip['circle']))
    if close_target == 'circle':
        checked(trip['aoi'].write('POST','/circles/' + trip['circle'] + '/close',dict(version=current['version'])))
    else:
        invitation = current['active_provider_invitation']
        checked(trip['aoi'].write('POST','/circle-provider-invitations/' + invitation['id'] + '/cancel',dict(version=invitation['version'],client_request_id='close-sharing')))
    with db.transaction() as conn:
        assert conn.execute('SELECT status FROM daytrip_redemptions WHERE id=?',(reserved['id'],)).fetchone()[0] == 'cancelled'
        assert tuple(conn.execute('SELECT * FROM daytrip_redemptions WHERE id=?',(used['id'],)).fetchone()) == used_before


def test_schema9_upgrade_repairs_only_stale_holds_and_is_atomic(trip, monkeypatch):
    from app.daytrip import schema as day_schema
    finish(trip,accept_all(trip,create(trip)))
    reward = benefit(trip)
    future = accept_all(trip,create(trip,day=3))
    stale = reservation(trip,trip['ren'],reward,future,'stale')
    keep = reservation(trip,trip['aoi'],reward,future,'keep')
    db = trip['harness'].app.state.database
    with db.transaction(True) as conn:
        for name in ('daytrip_release_participant','daytrip_release_circle','daytrip_release_invitation'):
            conn.execute('DROP TRIGGER ' + name)
        conn.execute('PRAGMA user_version=9')
        conn.execute("DELETE FROM travel_party_members WHERE party_id=? AND user_id='u-ren'",(trip['circle'],))
        assert conn.execute('SELECT status FROM daytrip_redemptions WHERE id=?',(stale['id'],)).fetchone()[0] == 'reserved'
        before = {table:[tuple(row) for row in conn.execute('SELECT * FROM ' + table + ' ORDER BY rowid')] for table in ('users','media','journal_journeys','daytrip_outings','daytrip_participants','daytrip_ledger')}
        keep_before = tuple(conn.execute('SELECT * FROM daytrip_redemptions WHERE id=?',(keep['id'],)).fetchone())
    ddl = day_schema.RELEASE_DDL
    monkeypatch.setattr(day_schema,'RELEASE_DDL',ddl + ('INVALID SQL',))
    with pytest.raises(sqlite3.OperationalError):
        day_schema.migrate(db)
    with db.transaction() as conn:
        assert conn.execute('PRAGMA user_version').fetchone()[0] == 9
        assert not conn.execute("SELECT 1 FROM sqlite_master WHERE name='daytrip_release_participant'").fetchone()
        assert conn.execute('SELECT status FROM daytrip_redemptions WHERE id=?',(stale['id'],)).fetchone()[0] == 'reserved'
    monkeypatch.setattr(day_schema,'RELEASE_DDL',ddl)
    day_schema.migrate(db)
    day_schema.migrate(db)
    with db.transaction() as conn:
        assert conn.execute('PRAGMA user_version').fetchone()[0] == 10
        assert conn.execute('SELECT status,version FROM daytrip_redemptions WHERE id=?',(stale['id'],)).fetchone()[:] == ('cancelled',2)
        assert tuple(conn.execute('SELECT * FROM daytrip_redemptions WHERE id=?',(keep['id'],)).fetchone()) == keep_before
        assert {table:[tuple(row) for row in conn.execute('SELECT * FROM ' + table + ' ORDER BY rowid')] for table in before} == before
        assert not conn.execute('PRAGMA foreign_key_check').fetchall()


def test_stale_provider_plan_consent_cannot_silently_use_new_price(trip):
    from app.marketplace.schemas import ProviderPlanInput
    plan = checked(trip['forest'].get('/provider-plans/forest-day'))
    updated = {key:value for key,value in plan.items() if key in ProviderPlanInput.model_fields}
    updated['price_yen'] = plan['price_yen'] + 900
    checked(trip['forest'].write('PATCH','/provider-plans/forest-day',updated))
    data = dict(title='古い料金で表示された開催',route_id=trip['route'],starts_at='2027-01-02T09:00:00+09:00',ends_at='2027-01-02T18:00:00+09:00',participant_ids=['u-aoi','u-ren','u-mio'],leader_id='u-aoi',plan_id='forest-day',client_request_id='stale-price')
    response = trip['aoi'].write('POST','/circles/' + trip['circle'] + '/outings',data)
    assert response.status_code == 409
    assert checked(trip['aoi'].get('/circles/' + trip['circle'] + '/outings'))['items'] == []


def test_provider_conflict_reload_uses_current_shared_access(trip):
    outing = finish(trip,accept_all(trip,create(trip)),verify=False)
    first = action(trip,trip['forest'],outing,'provider-confirm',participant_ids=['u-aoi'])
    old = trip['forest'].write('POST','/daytrip/outings/' + outing['id'] + '/provider-confirm',dict(version=outing['version'],participant_ids=['u-ren']))
    assert old.status_code == 409
    current = checked(trip['forest'].get('/daytrip/outings/' + outing['id']))
    assert current['is_provider'] is True and current['can_manage'] is False
    assert current['version'] == first['version']
    assert 'messages' not in current and 'plan_json' not in current
    assert trip['shore'].get('/daytrip/outings/' + outing['id']).status_code == 404
    assert checked(trip['ren'].get('/daytrip/outings/' + outing['id']))['is_provider'] is False
    circle_now = checked(trip['aoi'].get('/circles/' + trip['circle']))
    invitation = circle_now['active_provider_invitation']
    checked(trip['aoi'].write('POST','/circle-provider-invitations/' + invitation['id'] + '/cancel',dict(version=invitation['version'],client_request_id='stop-provider-access')))
    assert trip['forest'].get('/daytrip/outings/' + outing['id']).status_code == 404
