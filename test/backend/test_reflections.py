from datetime import datetime,timedelta,timezone
import json
import pytest
from app.reflections.extraction import extract,ASPECTS
from app.reflections.schema import migrate
from app.database import Database
from app.marketplace.schema import migrate as market_migrate
from app.journal.schema import migrate as journal_migrate
from app.circles.schema import migrate as circles_migrate
from app.circles.discovery_schema import migrate as discovery_migrate
from test_circles import circle,requirements,provider_invite,accept_provider


def ok(response):
    assert response.status_code==200,response.text
    return response.json()


def setup(harness,count=1,ready=True):
    clients={name:harness.client(name) for name in ('aoi','ren','mio','forest')}
    reflections=[]
    today=datetime.now(timezone(timedelta(hours=9))).date().isoformat()
    for n in range(count):
        created=circle(clients['aoi'],invitee_ids=['u-ren','u-mio'],client_request_id=f'circle-{n}')
        for invite in created['invitations']:
            client=clients[invite['invitee']['username']]
            ok(client.write('POST','/circle-invitations/'+invite['id']+'/respond',dict(decision='accepted',version=1,client_request_id=f'join-{n}')))
        requirements(clients['aoi'],created['id'],date_start=today)
        invitation,_=provider_invite(clients['aoi'],created['id'],f'invite-{n}')
        accept_provider(clients['forest'],invitation,f'accept-{n}')
        data=dict(invitation_id=invitation['id'],ended_on=today,trip_finished=True,client_request_id=f'reflect-{n}')
        reflection=ok(clients['aoi'].write('POST','/circles/'+created['id']+'/reflections',data))
        assert not reflection['ready_for_analysis']
        assert ok(clients['aoi'].write('POST','/circles/'+created['id']+'/reflections',data))['id']==reflection['id']
        if ready:
            consent_all(clients,reflection['id'])
        reflections.append(reflection)
    return clients,reflections


def consent_all(clients,rid):
    for name in ('aoi','ren','mio'):
        client=clients[name]
        current=ok(client.get('/reflections/'+rid))
        current=ok(client.write('PUT','/reflections/'+rid+'/participation',dict(used_service=True,version=current['my_state']['version'])))
        ok(client.write('PUT','/reflections/'+rid+'/consent',dict(allowed=True,version=current['my_state']['version'])))


def post(client,rid,key='post',body='森の旅案内の案内は分かりやすかった。'):
    return ok(client.write('POST','/reflections/'+rid+'/messages',dict(body=body,client_request_id=key)))


def public(client):
    return ok(client.get('/providers/forest-house/experience-summary'))


@pytest.mark.parametrize('text',[
    '森の旅案内の対応は良かったとは思えませんでした',
    '森の旅案内の説明は分かりやすかったわけではない',
    '森の旅案内の体験は楽しかったかどうか分かりません',
    '森の旅案内について、A社の対応は良かった',
    '対応は良かった','森の旅案内の対応は良かった。妻も満足した。',
    '森の旅案内の対応は良かったらしい','森の旅案内の対応は良かった(笑)',
    '森の旅案内の対応は良かった。天気もよかった。',
    '森の旅案内の対応は良かった。まだ利用していない。',
    '森の旅案内の対応は「良かった」','森の旅案内の対応は良かった？',
])
def test_conservative_extraction_rejects_uninterpreted_or_private_text(text):
    assert not extract(text,'森の旅案内')['eligible']


def test_extraction_full_clauses_and_mixed():
    result=extract('森の旅案内の案内は分かりやすかった。対応は遅かった。案内は不十分でした。','森の旅案内')
    assert result['eligible']
    assert {v['aspect_id']:v['sentiment'] for v in result['values']}==dict(guidance='mixed',response='negative',experience='excluded',price='excluded')


def test_no_analysis_before_all_explicit_usage_consent_and_no_legacy_chat(harness):
    clients,rows=setup(harness,ready=False)
    rid=rows[0]['id']; aoi=clients['aoi']
    assert aoi.write('PUT','/reflections/'+rid+'/consent',dict(allowed=True,version=1)).status_code==409
    message=post(aoi,rid)
    assert message['extraction']['status']=='waiting'
    with harness.app.state.database.transaction(True) as conn:
        assert conn.execute('SELECT auto_json FROM reflection_messages WHERE id=?',(message['id'],)).fetchone()[0] is None
    consent_all(clients,rid)
    result=ok(aoi.get('/reflections/'+rid))
    assert result['ready_for_analysis'] and result['messages'][0]['extraction']['status']=='auto_included'
    assert public(aoi)['status']=='insufficient'
    assert clients['forest'].get('/reflections/'+rid).status_code==404
    assert clients['forest'].write('PUT','/reflections/'+rid+'/participation',dict(used_service=True,version=1)).status_code==404
    assert harness.client().get('/providers/forest-house/experience-summary').status_code==401
    assert aoi.write('POST','/reflections/'+rid+'/messages',dict(body='x'*1001,client_request_id='long')).status_code==422
    with harness.app.state.database.transaction(True) as conn:
        conn.execute("INSERT INTO party_messages VALUES('private-chat',?,'u-ren','森の旅案内の価格は納得できました。','2026-01-01')",(rows[0]['circle_id'],))
        assert conn.execute('SELECT COUNT(*) FROM reflection_messages').fetchone()[0]==1
    assert len(ok(aoi.get('/reflections/'+rid))['messages'])==1


def test_threshold_distinct_authors_dedup_and_instant_revoke(harness):
    clients,rows=setup(harness,3)
    for row in rows:
        post(clients['aoi'],row['id'])
    assert public(clients['aoi'])['status']=='insufficient' # 3 circles, only one author
    for row in rows:
        post(clients['ren'],row['id'])
        post(clients['mio'],row['id'])
        post(clients['aoi'],row['id'],'repeat')
    summary=public(clients['aoi'])
    assert summary['status']=='available' and summary['trip_count']==3 and summary['ranking_signal']==1
    assert summary['facets'][0]['status']=='positive'
    assert all(value['trip_count'] is None for value in summary['facets'][1:])
    serialized=json.dumps(summary,ensure_ascii=False)
    for private in ('森の旅案内','u-aoi','created_at','ended_on','circle_id','body','分かりやすかった',rows[0]['id']):
        assert private not in serialized
    rid=rows[0]['id']; ren=clients['ren']
    current=ok(ren.get('/reflections/'+rid))
    ok(ren.write('PUT','/reflections/'+rid+'/consent',dict(allowed=False,version=current['my_state']['version'])))
    assert public(ren)['status']=='insufficient'
    discovered=ok(ren.get('/plan-discovery?community_id=peers'))
    assert all(item['experience_reference']['ranking_signal']==0 for item in discovered['items'])
    current=ok(ren.get('/reflections/'+rid))
    ok(ren.write('PUT','/reflections/'+rid+'/consent',dict(allowed=True,version=current['my_state']['version'])))
    assert public(ren)['trip_count']==3
    current=ok(ren.get('/reflections/'+rid))
    result=ok(ren.write('PUT','/reflections/'+rid+'/participation',dict(used_service=False,version=current['my_state']['version'])))
    assert not result['my_state']['consented'] and public(ren)['status']=='insufficient'


def test_mixed_and_small_polarity_categories_are_suppressed(harness):
    clients,rows=setup(harness,3)
    for row in rows:
        post(clients['aoi'],row['id'])
        post(clients['ren'],row['id'])
        post(clients['mio'],row['id'])
    post(clients['ren'],rows[0]['id'],'negative','森の旅案内の案内は不十分でした。')
    assert public(clients['aoi'])['status']=='insufficient' # positive 2 / mixed 1
    for row in rows[1:]:
        post(clients['ren'],row['id'],'negative','森の旅案内の案内は不十分でした。')
    result=public(clients['aoi'])
    assert result['facets'][0]['status']=='mixed' and result['trip_count']==3 and result['ranking_signal']==0


def test_author_review_version_edit_and_deletion(harness):
    clients,rows=setup(harness)
    rid=rows[0]['id'];aoi=clients['aoi']
    message=post(aoi,rid)
    values=[dict(aspect_id=key,sentiment='excluded') for key in ASPECTS]
    data=dict(version=1,source_version=1,values=values)
    path='/reflection-messages/'+message['id']
    assert clients['ren'].write('PUT',path+'/review',data).status_code==404
    reviewed=ok(aoi.write('PUT',path+'/review',data))
    assert reviewed['source_version']==1 and reviewed['version']==2 and reviewed['extraction']['status']=='author_corrected'
    assert aoi.write('PUT',path+'/review',data).status_code==409
    edited=ok(aoi.write('PUT',path,dict(version=2,body='森の旅案内の対応は遅かった。')))
    assert edited['source_version']==2 and edited['extraction']['status']=='auto_included'
    assert aoi.write('PUT',path+'/review',dict(version=3,source_version=1,values=values)).status_code==409
    ok(aoi.write('DELETE',path,dict(version=3)))
    assert ok(aoi.get('/reflections/'+rid))['messages']==[]
    with harness.app.state.database.transaction() as conn:
        row=conn.execute('SELECT body,auto_json,override_json FROM reflection_messages WHERE id=?',(message['id'],)).fetchone()
        assert tuple(row)==('',None,None)
    bad=post(aoi,rid,'private','森の旅案内の対応は良かった。家族の病気。')
    assert aoi.write('PUT','/reflection-messages/'+bad['id']+'/review',data).status_code==409


def test_cohort_changes_and_completion_reset_consent_and_history(harness):
    clients,rows=setup(harness)
    rid=rows[0]['id'];pid=rows[0]['circle_id'];aoi=clients['aoi']
    post(aoi,rid)
    with harness.app.state.database.transaction(True) as conn:
        conn.execute("DELETE FROM travel_party_members WHERE party_id=? AND user_id='u-mio'",(pid,))
        conn.execute("INSERT INTO travel_party_members VALUES(?,'u-mio')",(pid,))
    invalid=ok(aoi.get('/reflections/'+rid))
    assert not invalid['participant_set_current'] and not invalid['ready_for_analysis']
    fresh=ok(aoi.write('POST','/reflections/'+rid+'/participants-refresh',dict(version=invalid['version'])))
    assert fresh['epoch']==2 and fresh['messages']==[] and fresh['consented_count']==0
    consent_all(clients,rid)
    post(aoi,rid,'second')
    current=ok(aoi.get('/reflections/'+rid))
    ended=ok(aoi.write('PUT','/reflections/'+rid+'/completion',dict(trip_finished=False,version=current['version'])))
    assert not ended['ready_for_analysis']
    fresh=ok(aoi.write('PUT','/reflections/'+rid+'/completion',dict(trip_finished=True,version=ended['version'])))
    assert fresh['epoch']==3 and fresh['messages']==[] and fresh['usage_confirmed_count']==0


def test_schema6_preserves_prior_rows_and_rolls_back_failed_migration(tmp_path,monkeypatch):
    from app.reflections import schema
    db=Database(tmp_path/'old.db')
    db.initialize();market_migrate(db);journal_migrate(db);circles_migrate(db);discovery_migrate(db)
    with db.transaction(True) as conn:
        conn.execute("INSERT INTO journal_journeys VALUES('old-trip','u-aoi','前の旅',1,'2026-01-01')")
        names=[row[0] for row in conn.execute("SELECT name FROM sqlite_master WHERE type='table'")]
        before={name:[tuple(row) for row in conn.execute('SELECT * FROM "'+name+'" ORDER BY rowid')] for name in names}
    original=schema.DDL
    monkeypatch.setattr(schema,'DDL',original+('INVALID SQL',))
    with pytest.raises(Exception):
        migrate(db)
    with db.transaction() as conn:
        assert conn.execute('PRAGMA user_version').fetchone()[0]==5
        assert not conn.execute("SELECT 1 FROM sqlite_master WHERE name='reflection_sessions'").fetchone()
    monkeypatch.setattr(schema,'DDL',original)
    migrate(db);db.initialize();market_migrate(db);journal_migrate(db);circles_migrate(db);discovery_migrate(db);migrate(db)
    with db.transaction() as conn:
        assert conn.execute('PRAGMA user_version').fetchone()[0]==6
        assert before=={name:[tuple(row) for row in conn.execute('SELECT * FROM "'+name+'" ORDER BY rowid')] for name in names}


def test_reference_only_breaks_relevance_ties_and_retains_hard_filters(harness):
    clients,rows=setup(harness,3)
    for row in rows:
        for name in ('aoi','ren','mio'):
            post(clients[name],row['id'])
    aoi=clients['aoi']
    with harness.app.state.database.transaction(True) as conn:
        conn.execute("UPDATE grants SET use_matching=0 WHERE user_id='u-aoi' AND community_id='peers'")
    items=ok(aoi.get('/plan-discovery?community_id=peers'))['items']
    assert all(item['score']==0 for item in items)
    assert items[0]['experience_reference']['ranking_signal']==1
    with harness.app.state.database.transaction(True) as conn:
        conn.execute("UPDATE grants SET use_matching=1 WHERE user_id='u-aoi' AND community_id='peers'")
        conn.execute("UPDATE preferences SET tags='[\"coast\"]' WHERE user_id='u-aoi'")
    items=ok(aoi.get('/plan-discovery?community_id=peers'))['items']
    assert items[0]['plan']['id']=='shore-school' and items[0]['score']>items[1]['score']
    constrained=ok(aoi.get('/plan-discovery?community_id=peers&circle_id='+rows[0]['circle_id']))['items']
    assert [item['plan']['id'] for item in constrained]==['forest-six']


def test_account_membership_and_provider_role_changes_invalidate_consent(harness):
    clients,rows=setup(harness)
    rid=rows[0]['id']; aoi=clients['aoi']
    post(aoi,rid)
    for sql,revert in [
        ("UPDATE memberships SET status='left' WHERE user_id='u-ren' AND community_id='peers'","UPDATE memberships SET status='active' WHERE user_id='u-ren' AND community_id='peers'"),
        ("UPDATE users SET login_enabled=0 WHERE id='u-ren'","UPDATE users SET login_enabled=1 WHERE id='u-ren'"),
        ("INSERT INTO provider_staff VALUES('forest-house','u-ren',1)","DELETE FROM provider_staff WHERE provider_id='forest-house' AND user_id='u-ren'"),
    ]:
        with harness.app.state.database.transaction(True) as conn:
            conn.execute(sql)
            conn.execute(revert)
            # Existing leave triggers also remove accepted party membership.
            # Restore the test cohort to model a subsequent explicit re-join;
            # neither account nor community reactivation should do that itself.
            conn.execute("INSERT OR IGNORE INTO travel_party_members VALUES(?,'u-ren')",(rows[0]['circle_id'],))
        invalid=ok(aoi.get('/reflections/'+rid))
        assert not invalid['ready_for_analysis'] and not invalid['participant_set_current']
        ok(aoi.write('POST','/reflections/'+rid+'/participants-refresh',dict(version=invalid['version'])))
        consent_all(clients,rid)


def test_creation_rejects_unaccepted_provider_future_date_and_nonrepresentative(harness):
    clients,rows=setup(harness)
    row=rows[0]; aoi=clients['aoi'];today=datetime.now(timezone(timedelta(hours=9))).date()
    options=ok(aoi.get('/circles/'+row['circle_id']+'/reflection-options'))
    data=dict(invitation_id=options['items'][0]['invitation_id'],ended_on=today.isoformat(),trip_finished=True,client_request_id='new')
    assert clients['ren'].write('POST','/circles/'+row['circle_id']+'/reflections',data).status_code==404
    assert aoi.write('POST','/circles/'+row['circle_id']+'/reflections',dict(data,ended_on=(today+timedelta(days=1)).isoformat())).status_code==422
    created=circle(aoi,client_request_id='pending-circle')
    requirements(aoi,created['id'],date_start=today.isoformat())
    invite,_=provider_invite(aoi,created['id'],'pending-provider')
    assert aoi.write('POST','/circles/'+created['id']+'/reflections',dict(data,invitation_id=invite['id'])).status_code==404
