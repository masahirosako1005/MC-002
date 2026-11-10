from concurrent.futures import ThreadPoolExecutor
from datetime import date,datetime,timedelta,timezone
import json
import pytest
from app.database import Database
from app.marketplace.schema import migrate as market_migrate
from app.journal.schema import migrate as journal_migrate
from app.circles.schema import migrate as circles_migrate
from app.circles.discovery_schema import migrate as discovery_migrate
from app.reflections.schema import migrate as reflection_migrate
from app.occasions.schema import migrate
from app.occasions.service import Occasions
from app.circles.discovery import Discovery
from app.occasions import dates
from test_circles import circle,requirements
from test_discovery import set_preferences,edit_plan


def ok(response):
    assert response.status_code==200,response.text
    return response.json()


def setup(harness):
    aoi,ren,forest=harness.client('aoi'),harness.client('ren'),harness.client('forest')
    created=circle(aoi,invitee_ids=['u-ren'])
    invite=created['invitations'][0]
    ok(ren.write('POST','/circle-invitations/'+invite['id']+'/respond',dict(decision='accepted',version=1,client_request_id='join')))
    return aoi,ren,forest,created['id']


def create(aoi,**updates):
    today=dates.today_jst()
    data=dict(kind='anniversary',name='記念の日',month=today.month,day=today.day,repeats_annually=True,year=None,client_request_id='occasion')
    data.update(updates)
    return ok(aoi.write('POST','/me/occasions',data))


def share(aoi,occasion,pid,share_date=True,suggest=True):
    return ok(aoi.write('PUT','/me/occasions/'+occasion['id']+'/sharing',dict(version=occasion['version'],sharing=[dict(circle_id=pid,share_date=share_date,suggest=suggest)])))


def feed(client,pid):
    return ok(client.get('/occasion-suggestions?circle_id='+pid))['items']


def save(client,suggestion,plan='forest-six',key='save'):
    return ok(client.write('POST','/occasion-suggestions/'+suggestion['id']+'/candidate-cards',dict(plan_id=plan,plan_version=1,occasion_version=suggestion['occasion_version'],client_request_id=key)))


def cards(client,pid):
    return ok(client.get('/circles/'+pid+'/candidate-cards'))['items']


def normal_save(client,pid,key='normal',plan='forest-six'):
    return ok(client.write('POST','/circles/'+pid+'/candidate-cards',dict(plan_id=plan,plan_version=1,client_request_id=key)))


def test_private_defaults_birthday_minimization_crud_and_permissions(harness):
    aoi,ren,forest,pid=setup(harness)
    occasion=create(aoi,kind='birthday',name='誕生日')
    assert occasion['year'] is None and occasion['sharing']==[]
    assert feed(ren,pid)==[] and ok(ren.get('/circles/'+pid+'/occasions'))['items']==[]
    assert ok(ren.get('/me/occasions'))['items']==[]
    assert ren.get('/me/occasions/'+occasion['id']+'/preview?circle_id='+pid).status_code==404
    assert forest.get('/occasion-suggestions?circle_id='+pid).status_code==404
    assert harness.client().get('/me/occasions').status_code==401
    assert ren.write('DELETE','/me/occasions/'+occasion['id'],dict(version=1)).status_code==404
    invalid=dict(kind='birthday',name='誕生日',month=1,day=1,repeats_annually=True,year=1990,client_request_id='birth-year')
    assert aoi.write('POST','/me/occasions',invalid).status_code==422
    invalid.update(year=None,client_request_id='duplicate')
    assert aoi.write('POST','/me/occasions',invalid).status_code==409
    invalid.update(kind='anniversary',name='一度の日',month=2,day=30,repeats_annually=False,year=2027)
    assert aoi.write('POST','/me/occasions',invalid).status_code==422
    invalid.update(month=1,day=1,year=None)
    assert aoi.write('POST','/me/occasions',invalid).status_code==422
    anniversary=create(aoi,name='活動の日',client_request_id='other')
    body=dict(kind='anniversary',name='更新した日',month=anniversary['month'],day=anniversary['day'],repeats_annually=True,year=None,version=1)
    updated=ok(aoi.write('PUT','/me/occasions/'+anniversary['id'],body))
    assert updated['name']=='更新した日' and updated['version']==2
    assert aoi.write('PUT','/me/occasions/'+anniversary['id'],body).status_code==409
    ok(aoi.write('DELETE','/me/occasions/'+anniversary['id'],dict(version=2)))
    assert len(ok(aoi.get('/me/occasions'))['items'])==1


def test_date_only_sharing_is_separate_and_private_preview_stays_independent(harness):
    aoi,ren,_,pid=setup(harness)
    occasion=share(aoi,create(aoi),pid,suggest=False)
    dates_shared=ok(ren.get('/circles/'+pid+'/occasions'))['items']
    assert dates_shared[0]['name']=='記念の日' and not dates_shared[0]['suggestions_enabled']
    assert feed(ren,pid)==[]
    preview=ok(aoi.get('/me/occasions/'+occasion['id']+'/preview?circle_id='+pid))
    assert not preview['shared'] and preview['candidates']
    card=normal_save(aoi,pid)
    occasion=share(aoi,occasion,pid,False,False)
    assert ok(ren.get('/circles/'+pid+'/occasions'))['items']==[]
    assert cards(ren,pid)[0]['id']==card['id']
    bad=dict(version=occasion['version'],sharing=[dict(circle_id=pid,share_date=False,suggest=True)])
    assert aoi.write('PUT','/me/occasions/'+occasion['id']+'/sharing',bad).status_code==422


def test_stable_occurrence_state_per_user_year_rollover_and_leap_rules(harness,monkeypatch):
    aoi,ren,_,pid=setup(harness)
    monkeypatch.setattr(dates,'today_jst',lambda:date(2026,12,20))
    occasion=share(aoi,create(aoi,month=1,day=2),pid)
    suggestion=feed(aoi,pid)[0]
    assert suggestion['occurrence']['occurrence_year']==2027
    assert feed(aoi,pid)[0]['id']==suggestion['id']
    changed=ok(aoi.write('PUT','/occasion-suggestions/'+suggestion['id']+'/state',dict(state='later',version=0)))
    assert changed['state']=='later' and feed(ren,pid)[0]['state']=='new'
    assert aoi.write('PUT','/occasion-suggestions/'+suggestion['id']+'/state',dict(state='dismissed',version=0)).status_code==409
    ok(aoi.write('PUT','/occasion-suggestions/'+suggestion['id']+'/state',dict(state='dismissed',version=1)))
    assert feed(aoi,pid)[0]['state']=='dismissed'
    monkeypatch.setattr(dates,'today_jst',lambda:date(2027,12,20))
    next_year=feed(aoi,pid)[0]
    assert next_year['id']!=suggestion['id'] and next_year['state']=='new'
    assert aoi.write('PUT','/occasion-suggestions/'+suggestion['id']+'/state',dict(state='new',version=2)).status_code==404
    monkeypatch.setattr(dates,'today_jst',lambda:date(2027,2,20))
    leap=share(aoi,create(aoi,month=2,day=29,client_request_id='leap'),pid)
    chosen=next(item for item in feed(aoi,pid) if item['occasion_id']==leap['id'])
    assert chosen['occurrence']['occurrence_date']=='2027-02-28' and chosen['occurrence']['leap_adjusted']
    distant=ok(aoi.get('/me/occasions/'+occasion['id']+'/preview?circle_id='+pid))
    assert distant['occurrence'] is None and distant['candidates']==[]


def test_occasion_source_revocation_dedup_and_no_private_snapshot(harness):
    aoi,ren,_,pid=setup(harness)
    occasion=share(aoi,create(aoi),pid)
    suggestion=feed(ren,pid)[0]
    card=save(ren,suggestion)
    assert save(ren,suggestion)['id']==card['id']
    assert save(aoi,feed(aoi,pid)[0],key='another')['id']==card['id']
    assert len(cards(aoi,pid))==1
    body=json.dumps(card['snapshot'],ensure_ascii=False)
    assert occasion['name'] not in body and occasion['id'] not in body and 'occasion' not in body
    with harness.app.state.database.transaction() as conn:
        assert conn.execute('SELECT COUNT(*) FROM circle_provider_invitations').fetchone()[0]==0
    occasion=share(aoi,occasion,pid,suggest=False)
    assert feed(ren,pid)==[] and cards(ren,pid)==[]
    assert ren.write('POST','/occasion-suggestions/'+suggestion['id']+'/candidate-cards',dict(plan_id='forest-six',plan_version=1,occasion_version=suggestion['occasion_version'],client_request_id='save')).status_code==404
    occasion=share(aoi,occasion,pid)
    assert cards(ren,pid)==[] # old permission cannot revive old card
    refreshed=feed(ren,pid)[0]
    assert save(ren,refreshed,key='reshare')['id']==card['id']
    assert cards(ren,pid)[0]['snapshot']==card['snapshot']
    ok(aoi.write('DELETE','/me/occasions/'+occasion['id'],dict(version=occasion['version'])))
    assert cards(ren,pid)==[] and feed(ren,pid)==[]


@pytest.mark.parametrize('independent_first',[True,False])
def test_independent_saves_before_or_after_preserve_card_on_occasion_delete(harness,independent_first):
    aoi,ren,_,pid=setup(harness)
    if independent_first:
        normal_save(aoi,pid)
    occasion=share(aoi,create(aoi),pid)
    card=save(ren,feed(ren,pid)[0])
    if not independent_first:
        assert normal_save(aoi,pid)['id']==card['id']
    ok(aoi.write('DELETE','/me/occasions/'+occasion['id'],dict(version=occasion['version'])))
    assert cards(ren,pid)[0]['id']==card['id']


def test_multiple_origins_and_date_edit_expire_only_dependent_sources(harness):
    aoi,ren,_,pid=setup(harness)
    first=share(aoi,create(aoi),pid)
    second=share(aoi,create(aoi,name='二つ目',client_request_id='second'),pid)
    suggestions=feed(aoi,pid)
    card=save(aoi,next(s for s in suggestions if s['occasion_id']==first['id']))
    save(ren,next(s for s in suggestions if s['occasion_id']==second['id']))
    ok(aoi.write('DELETE','/me/occasions/'+first['id'],dict(version=first['version'])))
    assert cards(ren,pid)[0]['id']==card['id']
    body={key:second[key] for key in ('kind','name','month','day','repeats_annually','year','version')}
    body['day']=1 if body['day']!=1 else 2
    ok(aoi.write('PUT','/me/occasions/'+second['id'],body))
    assert cards(ren,pid)==[]


def test_owner_exit_latches_sharing_and_viewer_exit_denies_access(harness):
    aoi,ren,_,pid=setup(harness)
    occasion=share(ren,create(ren),pid)
    suggestion=feed(aoi,pid)[0]
    save(aoi,suggestion)
    with harness.app.state.database.transaction(True) as conn:
        conn.execute("UPDATE memberships SET status='left' WHERE user_id='u-ren' AND community_id='peers'")
        conn.execute("UPDATE memberships SET status='active' WHERE user_id='u-ren' AND community_id='peers'")
        conn.execute("INSERT OR IGNORE INTO travel_party_members VALUES(?,'u-ren')",(pid,))
    assert feed(aoi,pid)==[] and cards(aoi,pid)==[]
    own=ok(ren.get('/me/occasions'))['items'][0]
    assert not own['sharing'][0]['share_date']
    own=share(ren,own,pid)
    assert cards(aoi,pid)==[]
    fresh=feed(aoi,pid)[0]
    with harness.app.state.database.transaction(True) as conn:
        conn.execute("DELETE FROM travel_party_members WHERE party_id=? AND user_id='u-aoi'",(pid,))
    assert aoi.get('/occasion-suggestions?circle_id='+pid).status_code==404
    assert aoi.write('PUT','/occasion-suggestions/'+fresh['id']+'/state',dict(state='later',version=0)).status_code==404


def test_relevance_reacts_to_owner_grant_circle_tags_conditions_and_dates(harness):
    aoi,ren,forest,pid=setup(harness)
    occasion=share(aoi,create(aoi),pid)
    set_preferences(aoi,['coast'])
    current=ok(aoi.get('/circles/'+pid))
    ok(aoi.write('PUT','/circles/'+pid+'/preferences',dict(tags=[],version=current['version'])))
    own=feed(aoi,pid)[0]; other=feed(ren,pid)[0]
    assert own['candidates'][0]['plan']['id']=='shore-school'
    assert any('あなたが許可した関心' in reason for reason in own['candidates'][0]['reasons'])
    assert all('あなたが許可した関心' not in reason for item in other['candidates'] for reason in item['reasons'])
    set_preferences(aoi,['coast'],allowed=False)
    assert all(item['score']==0 for item in feed(ren,pid)[0]['candidates'])
    current=ok(aoi.get('/circles/'+pid))
    ok(aoi.write('PUT','/circles/'+pid+'/preferences',dict(tags=['cafe','nature'],version=current['version'])))
    assert feed(ren,pid)[0]['candidates'][0]['plan']['id']=='forest-six'
    requirements(aoi,pid,date_start=dates.today_jst().isoformat())
    assert [item['plan']['id'] for item in feed(aoi,pid)[0]['candidates']]==['forest-six']
    requirements(aoi,pid,date_start=dates.today_jst().isoformat(),planned_people=100,version=1)
    assert feed(aoi,pid)[0]['candidates']==[]
    requirements(aoi,pid,date_start=(dates.today_jst()+timedelta(days=1)).isoformat(),version=2)
    mismatch=feed(aoi,pid)[0]
    assert mismatch['candidates']==[] and '日付' in mismatch['notice']
    requirements(aoi,pid,date_start=dates.today_jst().isoformat(),version=3)
    start=(datetime.now(timezone.utc)+timedelta(days=2)).isoformat()
    end=(datetime.now(timezone.utc)+timedelta(days=3)).isoformat()
    edit_plan(forest,schedule_type='dated',starts_at=start,ends_at=end)
    assert feed(aoi,pid)[0]['candidates']==[]
    assert aoi.write('POST','/occasion-suggestions/'+own['id']+'/candidate-cards',dict(plan_id='forest-six',plan_version=1,occasion_version=occasion['version'],client_request_id='stale')).status_code==409


def test_occurrence_window_expiry_keeps_saved_source_and_unpublishing_changes_state(harness,monkeypatch):
    aoi,_,forest,pid=setup(harness)
    today=dates.today_jst()
    occasion=share(aoi,create(aoi),pid)
    suggestion=feed(aoi,pid)[0]
    save(aoi,suggestion)
    monkeypatch.setattr(dates,'today_jst',lambda:today+timedelta(days=1))
    assert feed(aoi,pid)==[] and len(cards(aoi,pid))==1
    edit_plan(forest,status='draft')
    assert cards(aoi,pid)[0]['current_state']=='unpublished'


def test_concurrent_duplicate_save_and_reopen_preserve_states(harness):
    aoi,_,_,pid=setup(harness)
    occasion=share(aoi,create(aoi),pid)
    suggestion=feed(aoi,pid)[0]
    service=Occasions(harness.app.state.database)
    def save_one(key):
        return service.save('u-aoi',suggestion['id'],dict(plan_id='forest-six',plan_version=1,occasion_version=occasion['version'],client_request_id=key))
    with ThreadPoolExecutor(max_workers=2) as pool:
        items=list(pool.map(save_one,('first','second')))
    assert items[0]['id']==items[1]['id']
    ok(aoi.write('PUT','/occasion-suggestions/'+suggestion['id']+'/state',dict(state='later',version=0)))
    reopened=Database(harness.settings.db_path)
    reopened.initialize();market_migrate(reopened);journal_migrate(reopened);circles_migrate(reopened);discovery_migrate(reopened);reflection_migrate(reopened);migrate(reopened)
    assert Occasions(reopened).suggestions('u-aoi',pid)['items'][0]['state']=='later'
    assert Discovery(reopened).cards('u-aoi',pid)['items'][0]['snapshot']==items[0]['snapshot']


def test_schema7_additive_preservation_and_failed_migration_rollback(tmp_path,monkeypatch):
    from app.occasions import schema
    db=Database(tmp_path/'schema6.db')
    db.initialize();market_migrate(db);journal_migrate(db);circles_migrate(db);discovery_migrate(db);reflection_migrate(db)
    with db.transaction(True) as conn:
        conn.execute("INSERT INTO journal_journeys VALUES('old-trip','u-aoi','前の旅',1,'2026-01-01')")
        conn.execute("INSERT INTO travel_parties VALUES('old-party','peers',NULL,'u-aoi','前の講','open','2026-01-01')")
        conn.execute("INSERT INTO travel_party_members VALUES('old-party','u-aoi')")
        conn.execute("INSERT INTO circle_candidate_cards VALUES('old-card','old-party','forest-six',1,'{}','u-aoi','2026-01-01',1)")
        conn.execute("INSERT INTO circle_provider_invitations VALUES('old-invite','old-party','forest-house','u-aoi','{}','closed',1,NULL,'2026-01-01','2026-01-01')")
        conn.execute("INSERT INTO reflection_sessions(id,party_id,provider_id,invitation_id,ended_on,trip_finished,participants_json,created_at) VALUES('old-reflection','old-party','forest-house','old-invite','2026-01-01',1,'[\"u-aoi\"]','2026-01-01')")
        conn.execute("INSERT INTO reflection_participants VALUES('old-reflection',1,'u-aoi',1,1,1,'2026-01-01')")
        conn.execute("INSERT INTO reflection_messages(id,reflection_id,epoch,author_id,body,created_at,updated_at) VALUES('old-message','old-reflection',1,'u-aoi','以前の振り返り','2026-01-01','2026-01-01')")
        names=[row[0] for row in conn.execute("SELECT name FROM sqlite_master WHERE type='table'")]
        before={name:[tuple(row) for row in conn.execute('SELECT * FROM "'+name+'" ORDER BY rowid')] for name in names}
    original=schema.DDL
    monkeypatch.setattr(schema,'DDL',original+('INVALID SQL',))
    with pytest.raises(Exception):
        migrate(db)
    with db.transaction() as conn:
        assert conn.execute('PRAGMA user_version').fetchone()[0]==6
        assert not conn.execute("SELECT 1 FROM sqlite_master WHERE name='occasions'").fetchone()
    monkeypatch.setattr(schema,'DDL',original)
    migrate(db)
    with db.transaction() as conn:
        assert conn.execute('PRAGMA user_version').fetchone()[0]==7
        assert before=={name:[tuple(row) for row in conn.execute('SELECT * FROM "'+name+'" ORDER BY rowid')] for name in names}
