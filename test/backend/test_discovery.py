from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timedelta, timezone
import json

import pytest

from app.database import Database
from app.marketplace.schema import migrate as marketplace_migrate
from app.journal.schema import migrate as journal_migrate
from app.circles.schema import migrate as circles_migrate
from app.circles.discovery_schema import migrate
from app.circles.discovery import Discovery
from app.marketplace.schedules import schedule_state, schedule_match
from test_circles import circle, requirements, provider_invite

JST=timezone(timedelta(hours=9))


def set_preferences(client,tags,allowed=True):
    prefs=client.get('/me/preferences').json()
    grants=[{**g,'use_for_matching':allowed} if g['community_id']=='peers' else g for g in prefs['grants']]
    response=client.write('PUT','/me/preferences',dict(tags=tags,learn_from_posts=False,grants=grants))
    assert response.status_code==200,response.text


def discover(client,pid=None):
    response=client.get('/plan-discovery?community_id=peers'+('&circle_id='+pid if pid else ''))
    assert response.status_code==200,response.text
    return response.json()


def edit_plan(client,**updates):
    current=client.get('/provider-plans/forest-six').json()
    keys=('title','summary','area','min_people','max_people','nights','price_yen','price_basis','price_scope','price_note','tags','itinerary','status','version','schedule_type','starts_at','ends_at')
    body={key:current[key] for key in keys}
    body.update(updates)
    return client.write('PATCH','/provider-plans/forest-six',body)


def future_period():
    starts=datetime.now(timezone.utc)+timedelta(days=20)
    ends=starts+timedelta(days=10)
    return starts.isoformat(),ends.isoformat()


def save(client,pid,plan='forest-six',version=1,key='save'):
    response=client.write('POST','/circles/'+pid+'/candidate-cards',dict(plan_id=plan,plan_version=version,client_request_id=key))
    assert response.status_code==200,response.text
    return response.json()


def test_relevance_uses_only_current_authorized_personal_interests(harness):
    aoi,ren=harness.client('aoi'),harness.client('ren')
    set_preferences(aoi,['coast'])
    first=discover(aoi)
    assert first['context']['profile_used'] and first['items'][0]['plan']['id']=='shore-school'
    assert first['items'][0]['score']==2 and any('あなたが許可した関心' in reason for reason in first['items'][0]['reasons'])
    set_preferences(ren,['games','fashion'])
    assert discover(aoi)==first
    set_preferences(aoi,['coast'],False)
    disabled=discover(aoi)
    assert not disabled['context']['profile_used']
    assert all(item['score']==0 and all('あなた' not in reason for reason in item['reasons']) for item in disabled['items'])
    assert harness.client('forest').get('/plan-discovery?community_id=peers').status_code==404
    assert aoi.get('/plan-discovery?community_id=missing').status_code==404


def test_circle_tag_updates_and_confirmed_conditions_change_results(harness):
    aoi,ren=harness.client('aoi'),harness.client('ren')
    set_preferences(aoi,[])
    created=circle(aoi,tags=['coast'])
    pid=created['id']
    before=discover(aoi,pid)
    assert not before['context']['profile_used'] and before['items'][0]['plan']['id']=='shore-school'
    assert before['items'][0]['score']==3
    assert ren.get('/plan-discovery?community_id=peers&circle_id='+pid).status_code==404
    changed=aoi.write('PUT','/circles/'+pid+'/preferences',dict(tags=['cafe'],version=created['version']))
    assert changed.status_code==200 and changed.json()['tags']==['cafe']
    assert discover(aoi,pid)['items'][0]['plan']['id'] in ('forest-six','forest-day')
    assert aoi.write('PUT','/circles/'+pid+'/preferences',dict(tags=['coast'],version=created['version'])).status_code==409
    requirements(aoi,pid)
    compatible=discover(aoi,pid)
    assert [item['plan']['id'] for item in compatible['items']]==['forest-six']
    assert compatible['context']['requirements_version']==1
    requirements(aoi,pid,planned_people=35,version=1)
    assert [item['plan']['id'] for item in discover(aoi,pid)['items']]==['shore-school']


def test_schedule_editor_requires_offset_order_and_stores_actual_period(harness):
    forest,shore=harness.client('forest'),harness.client('shore')
    original=forest.get('/provider-plans/forest-six').json()
    assert original['schedule_type']=='on_request' and original['starts_at'] is None
    starts,ends=future_period()
    for bad in (dict(schedule_type='dated'),dict(schedule_type='dated',starts_at=starts,ends_at=None),
                dict(schedule_type='dated',starts_at=ends,ends_at=starts),
                dict(schedule_type='dated',starts_at='2030-01-01T10:00:00',ends_at='2030-01-02T10:00:00'),
                dict(schedule_type='on_request',starts_at=starts,ends_at=ends),
                dict(schedule_type='dated',starts_at='1234567890',ends_at='1234567891'),
                dict(schedule_type='dated',starts_at=123,ends_at=234)):
        assert edit_plan(forest,**bad).status_code==422
    saved=edit_plan(forest,schedule_type='dated',starts_at=starts,ends_at=ends)
    assert saved.status_code==200,saved.text
    assert datetime.fromisoformat(saved.json()['starts_at'])==datetime.fromisoformat(starts)
    assert edit_plan(shore,title='他社変更').status_code==404


def test_dates_filter_discovery_legacy_selection_and_new_provider_accept(harness):
    aoi,forest=harness.client('aoi'),harness.client('forest')
    starts,ends=future_period()
    updated=edit_plan(forest,schedule_type='dated',starts_at=starts,ends_at=ends).json()
    pid=circle(aoi)['id']
    requirements(aoi,pid,date_start=(datetime.fromisoformat(starts).astimezone(JST).date()+timedelta(days=1)).isoformat())
    assert [i['plan']['id'] for i in discover(aoi,pid)['items']]==['forest-six']
    requirements(aoi,pid,date_start='2099-01-01',version=1)
    assert discover(aoi,pid)['items']==[]
    raw=dict(plan_id='forest-six',plan_version=updated['version'],requirements_version=2,share_note='',sharing_confirmed=True,version=aoi.get('/circles/'+pid).json()['version'],client_request_id='outside')
    assert aoi.write('POST','/circles/'+pid+'/provider-invitations',raw).status_code==409
    # The old selection endpoint must use the same schedule matcher too.
    legacy=aoi.write('POST','/communities/peers/travel-parties',dict(title='旧入口',member_ids=[])).json()['id']
    requirements(aoi,legacy,date_start='2099-01-01')
    old={key:value for key,value in raw.items() if key!='version'} | {'requirements_version':1}
    assert aoi.write('POST','/travel-parties/'+legacy+'/selections',old).status_code==409
    past=(datetime.now(timezone.utc)-timedelta(days=2)).isoformat()
    assert edit_plan(forest,schedule_type='dated',starts_at=past,ends_at=past).status_code==200
    assert 'forest-six' not in [i['plan']['id'] for i in discover(aoi)['items']]
    assert 'forest-six' not in [i['id'] for i in aoi.get('/provider-plans').json()['items']]
    assert any(i['id']=='forest-six' for i in forest.get('/provider-plans?provider_id=forest-house&mine=true').json()['items'])


def test_jst_date_boundary_and_exact_end_are_explicit():
    plan=dict(schedule_type='dated',starts_at='2099-01-01T15:30:00+00:00',ends_at='2099-01-02T14:59:00+00:00')
    assert schedule_match(plan,'2099-01-02')[2]==[]
    assert schedule_match(plan,'2099-01-01')[2]==['希望日が登録された開催期間外']
    assert schedule_state(plan,datetime.fromisoformat(plan['ends_at']))=='ongoing'
    assert schedule_state(plan,datetime.fromisoformat(plan['ends_at'])+timedelta(seconds=1))=='ended'


def test_save_is_shared_candidate_not_invitation_and_has_no_private_reason(harness):
    aoi,ren=harness.client('aoi'),harness.client('ren')
    set_preferences(aoi,['food','coast'])
    created=circle(aoi,tags=['cafe'],invitee_ids=['u-ren'])
    pid=created['id']
    assert ren.get('/circles/'+pid+'/candidate-cards').status_code==404
    stored=save(aoi,pid)
    assert all('あなた' not in reason for reason in stored['reasons'])
    assert 'preferences' not in json.dumps(stored['snapshot'])
    invite=created['invitations'][0]
    ren.write('POST','/circle-invitations/'+invite['id']+'/respond',dict(decision='accepted',version=1,client_request_id='accept'))
    assert ren.get('/circles/'+pid+'/candidate-cards').json()['items'][0]['id']==stored['id']
    assert save(ren,pid,key='second-user-save')['id']==stored['id']
    with harness.app.state.database.transaction() as conn:
        assert conn.execute('SELECT COUNT(*) FROM circle_candidate_cards WHERE party_id=?',(pid,)).fetchone()[0]==1
        assert conn.execute('SELECT COUNT(*) FROM circle_provider_invitations WHERE party_id=?',(pid,)).fetchone()[0]==0
        assert conn.execute('SELECT COUNT(*) FROM plan_selections WHERE party_id=?',(pid,)).fetchone()[0]==0
    assert aoi.write('POST','/circles/'+pid+'/candidate-cards',dict(plan_id='forest-day',plan_version=1,client_request_id='save')).status_code==409
    assert harness.client('forest').get('/circles/'+pid+'/candidate-cards').status_code==404


def test_cards_keep_snapshot_and_report_changed_unpublished_and_ended(harness):
    aoi,forest=harness.client('aoi'),harness.client('forest')
    pid=circle(aoi)['id']
    card=save(aoi,pid)
    title=card['snapshot']['title']
    edit_plan(forest,title='更新した森の行程')
    cards=lambda:aoi.get('/circles/'+pid+'/candidate-cards').json()['items']
    assert cards()[0]['current_state']=='updated'
    assert cards()[0]['snapshot']['title']==title and cards()[0]['current_plan']['title']=='更新した森の行程'
    assert save(aoi,pid,key='repeat')['snapshot']==card['snapshot']
    edit_plan(forest,status='draft',title='PRIVATE-DRAFT-TITLE')
    hidden=cards()[0]
    assert hidden['current_state']=='unpublished' and hidden['current_plan'] is None
    assert 'PRIVATE-DRAFT-TITLE' not in json.dumps(hidden)
    past=(datetime.now(timezone.utc)-timedelta(days=5)).isoformat()
    edit_plan(forest,status='published',schedule_type='dated',starts_at=past,ends_at=past)
    assert cards()[0]['current_state']=='ended'


def test_card_known_conditions_and_permissions_rechecked_on_read_and_save(harness):
    aoi,ren=harness.client('aoi'),harness.client('ren')
    pid=circle(aoi)['id']
    card=save(aoi,pid)
    requirements(aoi,pid,planned_people=35)
    assert aoi.get('/circles/'+pid+'/candidate-cards').json()['items'][0]['current_state']=='conditions_changed'
    assert aoi.write('POST','/circles/'+pid+'/candidate-cards',dict(plan_id='forest-day',plan_version=1,client_request_id='mismatch')).status_code==409
    assert ren.write('POST','/circles/'+pid+'/candidate-cards',dict(plan_id='shore-school',plan_version=1,client_request_id='unauthorized')).status_code==404
    assert aoi.write('POST','/circles/'+pid+'/candidate-cards',dict(plan_id='shore-school',plan_version=99,client_request_id='stale')).status_code==409


def test_card_concurrency_and_reopen_preserve_one_snapshot(harness):
    aoi=harness.client('aoi')
    pid=circle(aoi)['id']
    service=Discovery(harness.app.state.database)
    def add(key):
        return service.cards('u-aoi',pid,dict(plan_id='forest-six',plan_version=1,client_request_id=key))
    with ThreadPoolExecutor(max_workers=2) as pool:
        items=list(pool.map(add,('one','two')))
    assert items[0]['id']==items[1]['id']
    reopened=Database(harness.settings.db_path)
    reopened.initialize();marketplace_migrate(reopened);journal_migrate(reopened);circles_migrate(reopened);migrate(reopened)
    assert Discovery(reopened).cards('u-aoi',pid)['items'][0]['snapshot']==items[0]['snapshot']


def test_schema5_additive_and_failed_migration_preserves_schema4(tmp_path,monkeypatch):
    from app.circles import discovery_schema
    db=Database(tmp_path/'schema4.db')
    db.initialize();marketplace_migrate(db);journal_migrate(db);circles_migrate(db)
    with db.transaction(True) as conn:
        conn.execute("INSERT INTO journal_journeys VALUES('old-trip','u-aoi','前の旅',1,'2026-01-01')")
        conn.execute("INSERT INTO travel_parties VALUES('old-party','peers',NULL,'u-aoi','前の講','open','2026-01-01')")
        conn.execute("INSERT INTO travel_party_members VALUES('old-party','u-aoi')")
        names=[row[0] for row in conn.execute("SELECT name FROM sqlite_master WHERE type='table'")]
        before={name:[tuple(row) for row in conn.execute('SELECT * FROM "'+name+'" ORDER BY rowid')] for name in names}
    statements=discovery_schema.DDL
    monkeypatch.setattr(discovery_schema,'DDL',statements+('INVALID SQL',))
    with pytest.raises(Exception):
        migrate(db)
    with db.transaction() as conn:
        assert conn.execute('PRAGMA user_version').fetchone()[0]==4
        assert not conn.execute("SELECT 1 FROM sqlite_master WHERE name='circle_candidate_cards'").fetchone()
    monkeypatch.setattr(discovery_schema,'DDL',statements)
    migrate(db)
    with db.transaction() as conn:
        after={name:[tuple(row) for row in conn.execute('SELECT * FROM "'+name+'" ORDER BY rowid')] for name in names}
        assert before==after and conn.execute('PRAGMA user_version').fetchone()[0]==5


def test_matching_plan_after_first_100_rows_is_not_lost(harness):
    aoi=harness.client('aoi')
    pid=circle(aoi)['id']
    requirements(aoi,pid)
    with harness.app.state.database.transaction(True) as conn:
        original=conn.execute("SELECT body FROM provider_plans WHERE id='forest-six'").fetchone()[0]
        unsuitable=json.loads(original)
        unsuitable['min_people']=100
        unsuitable['max_people']=200
        for number in range(105):
            conn.execute("INSERT INTO provider_plans VALUES(?, 'forest-house',?, 'published',1,'2026-01-01')",(f'aaa-{number:03}',json.dumps(unsuitable)))
    assert [item['plan']['id'] for item in discover(aoi,pid)['items']]==['forest-six']
    turn=aoi.write('POST','/circles/'+pid+'/assistant-turns',dict(body='この条件で森に行きたい',client_request_id='after-100'))
    assert turn.status_code==200
    assert [item['plan']['id'] for item in turn.json()['candidates']]==['forest-six']


def test_high_relevance_after_first_100_rows_ranks_first_and_response_is_bounded(harness):
    aoi=harness.client('aoi')
    set_preferences(aoi,['coast'])
    with harness.app.state.database.transaction(True) as conn:
        original=conn.execute("SELECT body FROM provider_plans WHERE id='forest-six'").fetchone()[0]
        for number in range(105):
            conn.execute("INSERT INTO provider_plans VALUES(?, 'forest-house',?, 'published',1,'2026-01-01')",(f'aaa-{number:03}',original))
    result=discover(aoi)
    assert result['items'][0]['plan']['id']=='shore-school' and len(result['items'])==100


def test_public_catalog_filters_ended_before_response_limit(harness):
    aoi=harness.client('aoi')
    past=(datetime.now(timezone.utc)-timedelta(days=3)).isoformat()
    with harness.app.state.database.transaction(True) as conn:
        original=json.loads(conn.execute("SELECT body FROM provider_plans WHERE id='forest-six'").fetchone()[0])
        original.update(schedule_type='dated',starts_at=past,ends_at=past)
        for number in range(105):
            conn.execute("INSERT INTO provider_plans VALUES(?, 'forest-house',?, 'published',1,'2026-01-01')",(f'aaa-{number:03}',json.dumps(original)))
    assert {item['id'] for item in aoi.get('/provider-plans').json()['items']}=={'forest-six','forest-day','shore-school'}
