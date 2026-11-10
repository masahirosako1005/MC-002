from pathlib import Path
import sqlite3
import pytest
from app.database import Database
from app.marketplace.schema import migrate


def party(client):
    result = client.write('POST','/communities/peers/travel-parties',{'title':'仲間の旅を相談'})
    assert result.status_code == 200, result.text
    return result.json()['id']


def conditions(client,pid,people=6,**overrides):
    body=dict(planned_people=people,nights=2,budget_yen=30000,budget_basis='per_person',budget_scope='plan_only',date_start=None,interests=['nature','cafe'],departure_label='',version=0)
    body.update(overrides)
    result=client.write('PUT',f'/travel-parties/{pid}/requirements',body)
    assert result.status_code==200,result.text
    return result.json()


def select(client,pid,plan='forest-six',**overrides):
    data=dict(plan_id=plan,plan_version=1,requirements_version=1,share_note='集合場所を相談したいです。',sharing_confirmed=True,client_request_id='choose-1')
    data.update(overrides)
    return client.write('POST',f'/travel-parties/{pid}/selections',data)


def test_real_provider_round_trip_requires_selection_and_minimizes_disclosure(harness):
    aoi,forest,shore,ren=[harness.client(name) for name in ('aoi','forest','shore','ren')]
    pid=party(aoi)
    result=conditions(aoi,pid)
    assert result['active_account_count']==1 and result['requirements']['planned_people']==6
    secret=aoi.write('POST',f'/travel-parties/{pid}/messages',{'body':'非公開の内部事情','client_request_id':'private'})
    assert secret.status_code==200
    assert forest.get('/consultations').json()['items']==[]
    assert forest.get(f'/travel-parties/{pid}/messages').status_code==404
    assert ren.get(f'/travel-parties/{pid}').status_code==404
    preview=aoi.write('POST',f'/travel-parties/{pid}/selection-preview',dict(plan_id='forest-six',plan_version=1,requirements_version=1))
    assert preview.status_code==200
    assert forest.get('/consultations').json()['items']==[]
    consult=select(aoi,pid)
    assert consult.status_code==200,consult.text
    cid=consult.json()['id']
    visible=forest.get('/consultations/'+cid)
    assert visible.status_code==200 and '非公開の内部事情' not in visible.text
    assert 'interests' not in visible.json()['selection']['shared_conditions']
    assert shore.get('/consultations/'+cid).status_code==404
    assert ren.get('/consultations/'+cid).status_code==404
    for client,body,key in [(aoi,'集合は駅で可能ですか','ask'),(forest,'駅からの移動について相談しましょう','reply')]:
        response=client.write('POST',f'/consultations/{cid}/messages',dict(body=body,client_request_id=key))
        assert response.status_code==200
        assert client.write('POST',f'/consultations/{cid}/messages',dict(body=body,client_request_id=key)).json()==response.json()
    assert len(aoi.get(f'/consultations/{cid}/messages').json()['items'])==2


def test_capacity_nights_budget_scope_and_missing_date_are_not_fake_matches(harness):
    aoi=harness.client('aoi'); pid=party(aoi)
    conditions(aoi,pid,people=35)
    rec=aoi.write('POST',f'/travel-parties/{pid}/recommendations',{'version':1}).json()
    results={item['plan']['id']:item for item in rec['items']}
    assert results['shore-school']['eligible']
    assert not results['forest-six']['eligible']
    assert results['shore-school']['estimated_total_yen']==840000
    assert '希望日が未確認' in results['shore-school']['unknowns']
    assert select(aoi,pid).status_code==409
    assert select(aoi,pid,'shore-school').status_code==200
    assert aoi.get('/travel-parties/'+pid).json()['active_account_count']==1
    conditions(aoi,pid,people=35,budget_yen=800000,budget_basis='party_total',version=1)
    rec=aoi.write('POST',f'/travel-parties/{pid}/recommendations',{'version':2}).json()
    shore=next(i for i in rec['items'] if i['plan']['id']=='shore-school')
    assert not shore['eligible']
    conditions(aoi,pid,people=35,budget_scope='whole_trip',version=2)
    rec=aoi.write('POST',f'/travel-parties/{pid}/recommendations',{'version':3}).json()
    shore=next(i for i in rec['items'] if i['plan']['id']=='shore-school')
    assert shore['match_status']=='needs_confirmation'
    assert any('範囲が異なる' in value for value in shore['unknowns'])
    assert not any('予算以内' in value for value in shore['reasons'])


def test_conversation_numbers_are_drafts_not_confirmed_needs(harness):
    aoi=harness.client('aoi');pid=party(aoi)
    msg=aoi.write('POST',f'/travel-parties/{pid}/messages',{'body':'6人ではなく8人かも。2泊3日で1人3万円、引用の4万円は未確定。','client_request_id':'numbers'}).json()
    draft=aoi.write('POST',f'/travel-parties/{pid}/condition-drafts',{'message_ids':[msg['id']]}).json()
    assert draft['status']=='needs_confirmation'
    assert draft['candidates'][0]['candidates']['planned_people']==[6,8]
    assert draft['candidates'][0]['candidates']['budget_yen']==[30000,40000]
    assert aoi.get('/travel-parties/'+pid).json()['requirements'] is None
    other=party(aoi)
    assert aoi.write('POST',f'/travel-parties/{other}/condition-drafts',{'message_ids':[msg['id']]}).status_code==404


def test_selection_replay_version_snapshot_and_atomic_database_failure(harness):
    aoi,forest=harness.client('aoi'),harness.client('forest');pid=party(aoi);conditions(aoi,pid)
    with harness.app.state.database.transaction(True) as conn:
        conn.execute("CREATE TRIGGER reject_consult BEFORE INSERT ON consultations BEGIN SELECT RAISE(ABORT,'private-error'); END")
    failed=select(aoi,pid)
    assert failed.status_code==503 and 'private-error' not in failed.text
    with harness.app.state.database.transaction(True) as conn:
        assert conn.execute('SELECT COUNT(*) FROM plan_selections').fetchone()[0]==0
        conn.execute('DROP TRIGGER reject_consult')
    consult=select(aoi,pid).json()
    assert select(aoi,pid).json()==consult
    assert select(aoi,pid,share_note='異なる内容').status_code==409
    plan=forest.get('/provider-plans/forest-six').json()
    for field in ('id','provider','source_note'):
        plan.pop(field)
    plan['price_yen']=29000
    assert forest.write('PATCH','/provider-plans/forest-six',plan).status_code==200
    assert aoi.get('/consultations/'+consult['id']).json()['selection']['plan']['price_yen']==28000
    assert select(aoi,pid,client_request_id='new-choice').status_code==409
    newer=select(aoi,pid,plan_version=2,client_request_id='new-choice').json()
    assert newer['id']!=consult['id']
    assert aoi.get('/consultations/'+consult['id']).json()['status']=='closed'
    assert aoi.write('POST','/consultations/'+consult['id']+'/messages',{'body':'閉鎖後','client_request_id':'closed'}).status_code==409


def test_provider_authorization_plan_validation_and_revocation(harness):
    aoi,forest,shore=harness.client('aoi'),harness.client('forest'),harness.client('shore')
    assert forest.get('/marketplace/capabilities').json()['providers'][0]['id']=='forest-house'
    assert aoi.get('/marketplace/capabilities').json()['providers']==[]
    plan=forest.get('/provider-plans/forest-day').json()
    for field in ('id','provider','source_note'):
        plan.pop(field)
    plan.update(version=0,status='draft')
    assert aoi.write('POST','/providers/forest-house/plans',plan).status_code==404
    assert shore.write('POST','/providers/forest-house/plans',plan).status_code==404
    created=forest.write('POST','/providers/forest-house/plans',plan)
    assert created.status_code==200
    assert aoi.get('/provider-plans/'+created.json()['id']).status_code==404
    assert forest.get('/provider-plans?provider_id=forest-house&mine=true').status_code==200
    plan.update(nights=2,status='published')
    assert forest.write('POST','/providers/forest-house/plans',plan).status_code==422
    pid=party(aoi);conditions(aoi,pid);cid=select(aoi,pid).json()['id']
    with harness.app.state.database.transaction(True) as conn:
        conn.execute("UPDATE provider_staff SET active=0 WHERE user_id='provider-forest'")
    assert forest.get('/consultations/'+cid).status_code==404
    assert forest.get('/consultations').json()['items']==[]


def test_requirements_strict_input_and_csrf(harness):
    aoi=harness.client('aoi');pid=party(aoi)
    body=dict(planned_people=True,nights=2,version=0)
    assert aoi.write('PUT',f'/travel-parties/{pid}/requirements',body).status_code==422
    assert aoi.write('PUT',f'/travel-parties/{pid}/requirements',dict(planned_people=6,nights=2,budget_yen=30000,version=0)).status_code==422
    assert aoi.write('POST',f'/communities/peers/travel-parties',{'title':'不正','member_ids':['u-ren']}).status_code==422
    aoi.client.headers['X-CSRF-Token']='invalid'
    assert aoi.write('POST',f'/travel-parties/{pid}/messages',{'body':'禁止','client_request_id':'csrf'}).status_code==403


def test_schema_migration_repeat_and_backup_restore(tmp_path):
    db=Database(tmp_path/'old.db');db.initialize()
    with db.transaction() as conn:
        original_users=conn.execute('SELECT COUNT(*) FROM users').fetchone()[0]
        assert conn.execute('PRAGMA user_version').fetchone()[0]==1
    migrate(db);migrate(db);db.initialize()
    with db.transaction() as conn:
        assert conn.execute('PRAGMA user_version').fetchone()[0]==2
        assert conn.execute('SELECT COUNT(*) FROM users').fetchone()[0]==original_users+2
        assert conn.execute('PRAGMA foreign_key_check').fetchall()==[]
        restored=sqlite3.connect(tmp_path/'restored.db');conn.backup(restored);restored.close()
    copy=Database(tmp_path/'restored.db');copy.initialize();migrate(copy)
    with copy.transaction() as conn:
        assert conn.execute('PRAGMA integrity_check').fetchone()[0]=='ok'
        assert conn.execute('SELECT COUNT(*) FROM provider_plans').fetchone()[0]==3


def test_migration_failure_rolls_back_schema_and_accounts(tmp_path):
    db=Database(tmp_path/'failure.db');db.initialize()
    with db.transaction(True) as conn:
        conn.execute("CREATE TRIGGER fail_provider BEFORE INSERT ON users BEGIN SELECT RAISE(ABORT,'failure'); END")
    with pytest.raises(sqlite3.IntegrityError):
        migrate(db)
    with db.transaction(True) as conn:
        assert conn.execute('PRAGMA user_version').fetchone()[0]==1
        assert conn.execute("SELECT 1 FROM sqlite_master WHERE type='table' AND name='providers'").fetchone() is None
        conn.execute('DROP TRIGGER fail_provider')
    migrate(db)


def test_representative_closes_plan_before_leaving_and_loses_access(harness):
    aoi=harness.client('aoi')
    cid=aoi.write('POST','/communities',{'name':'家族の旅','description':''}).json()['id']
    pid=aoi.write('POST',f'/communities/{cid}/travel-parties',{'title':'6人の旅行'}).json()['id']
    conditions(aoi,pid)
    consult=select(aoi,pid).json()
    assert aoi.write('POST',f'/communities/{cid}/leave').status_code==409
    assert aoi.write('POST',f'/travel-parties/{pid}/close').json()['status']=='closed'
    assert aoi.get('/consultations/'+consult['id']).json()['status']=='closed'
    assert select(aoi,pid,client_request_id='after-close').status_code==409
    assert aoi.write('POST',f'/communities/{cid}/leave').status_code==200
    assert aoi.get('/travel-parties/'+pid).status_code==404
    assert aoi.get('/consultations/'+consult['id']).status_code==404


def test_disabled_provider_staff_cannot_close_as_ordinary_traveler(harness):
    aoi,forest=harness.client('aoi'),harness.client('forest')
    pid=party(aoi);conditions(aoi,pid);consult=select(aoi,pid).json()
    # Model a dual-role account explicitly, without granting representative power.
    with harness.app.state.database.transaction(True) as conn:
        conn.execute("INSERT INTO memberships VALUES('peers','provider-forest','member','active')")
        conn.execute('INSERT INTO travel_party_members VALUES(?,?)',(pid,'provider-forest'))
        conn.execute("UPDATE providers SET active=0 WHERE id='forest-house'")
    visible=forest.get('/consultations/'+consult['id'])
    assert visible.status_code==200 and not visible.json()['can_close']
    assert forest.write('POST','/consultations/'+consult['id']+'/close',{'version':1}).status_code==404
    assert aoi.get('/consultations/'+consult['id']).json()['status']=='open'


def test_concurrent_party_creation_and_leave_cannot_orphan_representative(harness):
    from concurrent.futures import ThreadPoolExecutor
    from threading import Barrier
    from fastapi import HTTPException
    from app.marketplace.service import Marketplace
    aoi=harness.client('aoi')
    cid=aoi.write('POST','/communities',{'name':'計画と退出の競合','description':''}).json()['id']
    gate=Barrier(2)
    marketplace=Marketplace(harness.app.state.database)

    def attempt(create):
        gate.wait(timeout=5)
        try:
            if create:
                marketplace.create_party('u-aoi',cid,{'title':'旅の予定','ko_group_id':None,'member_ids':[]})
            else:
                harness.app.state.service.leave('u-aoi',cid)
            return 200
        except HTTPException as exc:
            return exc.status_code

    with ThreadPoolExecutor(max_workers=2) as pool:
        statuses=list(pool.map(attempt,[True,False]))
    assert statuses.count(200)==1
    assert any(code in (404,409) for code in statuses)
    with harness.app.state.database.transaction() as conn:
        assert conn.execute("SELECT COUNT(*) FROM travel_parties p JOIN memberships m ON m.community_id=p.community_id AND m.user_id=p.representative_id WHERE p.status='open' AND m.status='left'").fetchone()[0]==0
