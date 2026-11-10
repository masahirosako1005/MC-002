import json
from concurrent.futures import ThreadPoolExecutor
from datetime import UTC, datetime, timedelta

import pytest
from fastapi import HTTPException

from app.omikuji import schema
from app.omikuji import service as module
from app.omikuji.service import Omikuji


def checked(response):
    assert response.status_code == 200, response.text
    return response.json()


@pytest.fixture
def game(harness, monkeypatch):
    clock = [datetime(2027, 1, 10, 3, tzinfo=UTC)]
    monkeypatch.setattr(module, "clock_now", lambda: clock[0])
    clients = {name: harness.client(name) for name in ("aoi", "ren", "mio", "forest", "shore")}
    return dict(harness=harness, clock=clock, service=Omikuji(harness.app.state.database), **clients)



def configure(game, provider='forest-house', client='forest', budget=10000, enabled=True):
    current = checked(game[client].get('/omikuji/provider'))['providers'][0]
    return game[client].write('PUT', '/omikuji/provider/policy', dict(provider_id=provider, enabled=enabled, monthly_budget_yen=budget, version=current['version']))


def code(game, client='forest', provider='forest-house'):
    return checked(game[client].write('POST', '/omikuji/provider/codes', dict(provider_id=provider)))['code']


def draw(game, value, client='aoi', key='drawing-request-001'):
    return game[client].write('POST', '/omikuji/draw', dict(code=value, client_request_id=key))


def test_disabled_default_auth_and_explicit_provider_consent(game):
    guest = game['harness'].client()
    assert guest.get('/omikuji').status_code == 401
    current = checked(game['forest'].get('/omikuji/provider'))
    assert current['providers'][0]['enabled'] is False
    assert current['providers'][0]['version'] == 0
    assert game['forest'].write('POST', '/omikuji/provider/codes', dict(provider_id='forest-house')).status_code == 409
    assert game['aoi'].write('PUT', '/omikuji/provider/policy', dict(provider_id='forest-house',enabled=True,monthly_budget_yen=10000,version=0)).status_code == 404
    assert configure(game, budget=299).status_code == 409
    assert checked(configure(game))['version'] == 1
    wrong = game['forest'].write('PUT','/omikuji/provider/policy',dict(provider_id='forest-house',enabled=True,monthly_budget_yen=10000,version=0))
    assert wrong.status_code == 409
    assert game['shore'].write('POST','/omikuji/provider/codes',dict(provider_id='forest-house')).status_code == 404


def test_code_hashed_once_only_idempotency_and_private_history(game, monkeypatch):
    checked(configure(game)); monkeypatch.setattr(module, 'sample', lambda level: 200)
    value = code(game)
    with game['harness'].app.state.database.transaction() as conn:
        stored = dict(conn.execute('SELECT * FROM omikuji_codes').fetchone())
    assert value not in json.dumps(stored) and len(stored['code_hash']) == 64
    first = checked(draw(game, value))
    assert checked(draw(game, value)) == first
    other = '000001' if value != '000001' else '000002'
    assert draw(game, other).status_code == 400
    assert draw(game, value, key='different-request').status_code == 409
    assert draw(game, value, client='ren', key='ren-request-001').status_code == 404
    assert checked(game['ren'].get('/omikuji'))['draws'] == []
    assert checked(game['shore'].get('/omikuji/provider'))['rewards'] == []
    own = checked(game['aoi'].get('/omikuji'))
    assert not own['can_draw'] and own['draws'][0]['id'] == first['id']
    assert 'user_id' not in json.dumps(own) and 'code_hash' not in json.dumps(own)
    assert 'code' not in checked(game['forest'].get('/omikuji/provider'))


def test_expiration_and_failed_attempts_persist_without_consuming_code(game):
    checked(configure(game));value=code(game)
    game['clock'][0] += timedelta(minutes=10)
    assert draw(game,value).status_code == 404
    for i in range(4):
        assert draw(game,'999999',key=f'invalid-{i:08}').status_code == 404
    assert draw(game,'999999',key='sixth-request').status_code == 429
    fresh_service = Omikuji(game['harness'].app.state.database)
    with pytest.raises(HTTPException) as error:
        fresh_service.draw('u-aoi',dict(code='999999',client_request_id='seventh-request'))
    assert error.value.status_code == 429
    with game['harness'].app.state.database.transaction() as conn:
        assert conn.execute('SELECT consumed_at FROM omikuji_codes').fetchone()[0] is None
        assert conn.execute('SELECT COUNT(*) FROM omikuji_draws').fetchone()[0] == 0
    game['clock'][0] += timedelta(minutes=1)
    assert draw(game,'999999',key='later-request').status_code == 404


def test_month_limit_uses_jst_and_global_provider_scope(game, monkeypatch):
    checked(configure(game)); checked(configure(game,'shore-school','shore'));monkeypatch.setattr(module,'sample',lambda level:0)
    game['clock'][0] = datetime(2027,1,31,14,59,59,tzinfo=UTC)
    first=checked(draw(game,code(game)))
    assert first['month']=='2027-01' and first['reward'] is None
    second_code=code(game,'shore','shore-school')
    assert draw(game,second_code,key='same-month-other-provider').status_code==409
    game['clock'][0] += timedelta(seconds=1)
    second=checked(draw(game,second_code,key='next-month-request'))
    assert second['month']=='2027-02'
    assert len(checked(game['aoi'].get('/omikuji'))['draws'])==2


def test_eligible_rank_controls_odds_not_personal_claims(game, monkeypatch):
    checked(configure(game))
    monkeypatch.setattr(module.Daytrip,'rank_states',staticmethod(lambda conn,uid,at=None: ({'rank':10,'name':'勧進元'},{'rank':1,'name':'新客'})))
    seen=[]
    monkeypatch.setattr(module,'sample',lambda level:seen.append(level) or 100)
    state=checked(game['aoi'].get('/omikuji'))
    assert state['rank']['level']==1 and state['personal_rank']['level']==10
    assert [x['probability_percent'] for x in state['odds']]==[50,40,10,0]
    assert checked(draw(game,code(game)))['rank_level']==1 and seen==[1]


def test_all_rank_probability_boundaries_use_server_random(monkeypatch):
    for level in range(1,11):
        outcomes=[]
        for number in range(100):
            monkeypatch.setattr(module.secrets,'randbelow',lambda maximum,n=number:n)
            outcomes.append(module.sample(level))
        assert {amount:outcomes.count(amount) for amount in (0,100,200,300)} == {row['amount_yen']:row['probability_percent'] for row in module.odds(level)}
    assert module.odds(10)[0]['probability_percent'] < module.odds(1)[0]['probability_percent']


def test_budget_atomic_race_and_cannot_reduce_below_issued(game, monkeypatch):
    checked(configure(game,budget=300)); values=[code(game),code(game)]
    monkeypatch.setattr(module,'sample',lambda level:300)
    def attempt(pair):
        uid,value=pair
        try:return game['service'].draw(uid,dict(code=value,client_request_id='race-request-001'))
        except HTTPException as error:return error.status_code
    with ThreadPoolExecutor(max_workers=2) as pool:
        results=list(pool.map(attempt,zip(['u-aoi','u-ren'],values,strict=True)))
    assert len([x for x in results if isinstance(x,dict)])==1 and 409 in results
    provider=checked(game['forest'].get('/omikuji/provider'))['providers'][0]
    assert provider['issued_yen']==300 and provider['remaining_yen']==0
    assert configure(game,budget=299,enabled=False).status_code==409
    assert checked(configure(game,budget=300,enabled=False))['enabled'] is False
    with game['harness'].app.state.database.transaction() as conn:
        assert conn.execute('SELECT COUNT(*) FROM omikuji_codes WHERE consumed_at IS NOT NULL').fetchone()[0]==1


def test_same_user_concurrent_month_requests_only_once(game, monkeypatch):
    checked(configure(game)); values=[code(game),code(game)];monkeypatch.setattr(module,'sample',lambda level:100)
    def attempt(pair):
        i,value=pair
        try:return game['service'].draw('u-aoi',dict(code=value,client_request_id=f'user-race-{i:08}'))
        except HTTPException as error:return error.status_code
    with ThreadPoolExecutor(max_workers=2) as pool:results=list(pool.map(attempt,enumerate(values)))
    assert len([x for x in results if isinstance(x,dict)])==1 and 409 in results
    with game['harness'].app.state.database.transaction() as conn:
        assert conn.execute('SELECT COUNT(*) FROM omikuji_draws').fetchone()[0]==1


def test_reward_redemption_staff_scope_price_noncombination_and_expiry(game, monkeypatch):
    checked(configure(game));monkeypatch.setattr(module,'sample',lambda level:200)
    reward=checked(draw(game,code(game)))['reward'];path='/omikuji/rewards/'+reward['id']+'/redeem'
    body=dict(purchase_yen=1000,no_other_discount=True)
    assert game['aoi'].write('POST',path,body).status_code==404
    assert game['shore'].write('POST',path,body).status_code==404
    assert game['forest'].write('POST',path,dict(purchase_yen=199,no_other_discount=True)).status_code==422
    assert game['forest'].write('POST',path,dict(purchase_yen=1000,no_other_discount=False)).status_code==422
    checked(configure(game,enabled=False))
    assert checked(game['forest'].write('POST',path,body))['status']=='redeemed'
    assert game['forest'].write('POST',path,body).status_code==409
    checked(configure(game)); second=checked(draw(game,code(game),client='ren',key='ren-second-reward'))['reward']
    game['clock'][0]+=timedelta(days=30)
    assert game['forest'].write('POST','/omikuji/rewards/'+second['id']+'/redeem',body).status_code==409
    assert checked(game['ren'].get('/omikuji'))['draws'][0]['reward']['status']=='expired'


def test_csrf_extra_fields_and_no_seed_auto_enable(game):
    original=game['aoi'].client.headers.pop('X-CSRF-Token')
    assert draw(game,'123456').status_code==403
    game['aoi'].client.headers['X-CSRF-Token']=original
    assert game['aoi'].write('POST','/omikuji/draw',dict(code='123456',client_request_id='request-001',rank_level=10)).status_code==422
    assert game['aoi'].write('POST','/omikuji/draw',dict(code='12345',client_request_id='request-001')).status_code==422
    assert configure(game,budget=10001).status_code==422
    for invalid in ('false', 'true', 0, 1):
        assert configure(game,enabled=invalid).status_code==422
    db=game['harness'].app.state.database
    with db.transaction() as conn:
        assert conn.execute('SELECT COUNT(*) FROM omikuji_policies').fetchone()[0]==0
        assert conn.execute('PRAGMA user_version').fetchone()[0]==12
    schema.migrate(db)
    with db.transaction() as conn:
        assert conn.execute("SELECT value FROM settings WHERE key='omikuji-schema'").fetchone()[0]=='1'
        assert conn.execute('PRAGMA foreign_key_check').fetchall()==[]


def test_independent_schema_rollback_and_repeat_preserves_application(game, monkeypatch):
    import sqlite3
    db=game['harness'].app.state.database
    with db.transaction(True) as conn:
        user_count=conn.execute('SELECT COUNT(*) FROM users').fetchone()[0]
        for table in ('omikuji_rewards','omikuji_draws','omikuji_codes','omikuji_policies','omikuji_attempts'):
            conn.execute('DROP TABLE '+table)
        conn.execute("DELETE FROM settings WHERE key IN ('omikuji-schema','omikuji-code-pepper')")
    original=schema.DDL
    monkeypatch.setattr(schema,'DDL',original+('INVALID SQL',))
    with pytest.raises(sqlite3.Error):schema.migrate(db)
    with db.transaction() as conn:
        assert conn.execute("SELECT COUNT(*) FROM sqlite_master WHERE name LIKE 'omikuji_%'").fetchone()[0]==0
        assert conn.execute('SELECT COUNT(*) FROM users').fetchone()[0]==user_count
        assert conn.execute('PRAGMA user_version').fetchone()[0]==12
    monkeypatch.setattr(schema,'DDL',original)
    schema.migrate(db);schema.migrate(db)
    with db.transaction() as conn:
        assert conn.execute("SELECT value FROM settings WHERE key='omikuji-schema'").fetchone()[0]=='1'
        assert conn.execute('PRAGMA foreign_key_check').fetchall()==[]


def test_redeem_race_and_inactive_provider_authority(game, monkeypatch):
    checked(configure(game));monkeypatch.setattr(module,'sample',lambda level:100)
    reward=checked(draw(game,code(game)))['reward']
    with game['harness'].app.state.database.transaction() as conn:
        uid=conn.execute("SELECT user_id FROM provider_staff WHERE provider_id='forest-house'").fetchone()[0]
    def redeem(_):
        try:return game['service'].redeem(uid,reward['id'],dict(purchase_yen=1000,no_other_discount=True))
        except HTTPException as error:return error.status_code
    with ThreadPoolExecutor(max_workers=2) as pool:results=list(pool.map(redeem,range(2)))
    assert len([x for x in results if isinstance(x,dict)])==1 and 409 in results
    with game['harness'].app.state.database.transaction(True) as conn:
        conn.execute("UPDATE provider_staff SET active=0 WHERE provider_id='forest-house'")
    assert game['forest'].write('POST','/omikuji/provider/codes',dict(provider_id='forest-house')).status_code==404
    assert checked(game['forest'].get('/omikuji/provider'))['providers']==[]
