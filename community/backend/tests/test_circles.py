from concurrent.futures import ThreadPoolExecutor
import asyncio
import json

from fastapi import HTTPException
import pytest

from app.circles.service import Circles
from app.circles.schema import migrate
from app.database import Database
from app.journal.schema import migrate as journal_migrate
from app.marketplace.schema import migrate as marketplace_migrate


def circle(client, **overrides):
    data = dict(community_id='peers',title='森の休日',mode='manual',tags=['nature','cafe'],desired_count=3,invitee_ids=[],client_request_id='circle-one')
    data.update(overrides)
    response = client.write('POST','/circles',data)
    assert response.status_code == 200,response.text
    return response.json()


def requirements(client, pid, **overrides):
    data = dict(planned_people=6,nights=2,budget_yen=30000,budget_basis='per_person',budget_scope='plan_only',date_start='2027-03-01',interests=['nature','cafe'],departure_label='',version=0)
    data.update(overrides)
    response = client.write('PUT','/travel-parties/'+pid+'/requirements',data)
    assert response.status_code == 200,response.text
    return response.json()


def provider_invite(client, pid, key='provider-invite'):
    current = client.get('/circles/'+pid).json()
    data = dict(plan_id='forest-six',plan_version=1,requirements_version=current['requirements']['version'],share_note='森をゆっくり歩きたいです',sharing_confirmed=True,version=current['version'],client_request_id=key)
    response = client.write('POST','/circles/'+pid+'/provider-invitations',data)
    assert response.status_code == 200,response.text
    return response.json(),data


def accept_provider(client, invitation, key='provider-accept'):
    data = dict(decision='accepted',version=invitation['version'],client_request_id=key)
    response = client.write('POST','/circle-provider-invitations/'+invitation['id']+'/respond',data)
    assert response.status_code == 200,response.text
    return response.json()


def proposal_data(version=0,key='quote-one'):
    return dict(title='森とカフェをめぐる行程案',date_start='2027-03-01',itinerary=[dict(day=day,period='afternoon',place='森の散策路',description='歩く時間を相談',travel_minutes=None) for day in (1,2,3)],
                estimated_price_yen=28000,price_basis='per_person',price_scope='plan_only',price_note='宿泊と体験。交通費は別',unknowns=['空席と営業は未確認'],version=version,client_request_id=key)


def setup_shared(harness, with_member=False):
    aoi,forest = harness.client('aoi'),harness.client('forest')
    created = circle(aoi,invitee_ids=['u-ren'] if with_member else [])
    if with_member:
        ren = harness.client('ren')
        invitation = created['invitations'][0]
        assert ren.write('POST','/circle-invitations/'+invitation['id']+'/respond',dict(decision='accepted',version=1,client_request_id='join')).status_code == 200
    requirements(aoi,created['id'])
    invitation,_ = provider_invite(aoi,created['id'])
    accepted = accept_provider(forest,invitation)
    return aoi,forest,created,accepted


def test_bootstrap_hides_accounts_and_all_circles_require_auth(harness):
    anon = harness.client()
    body = anon.get('/bootstrap').json()
    assert set(body) == {'tags','model'}
    assert not any(text in json.dumps(body) for text in ('aoi','forest','藤沢','森の旅案内'))
    assert anon.get('/circles').status_code == 401
    assert anon.get('/circles/help').status_code == 401
    aoi = harness.client('aoi')
    assert not aoi.get('/circles/help').json()['external_ai_enabled']
    assert aoi.write('POST','/circles/candidates',dict(community_id='peers',tags=['cafe'],desired_count=3),headers={'X-CSRF-Token':'bad'}).status_code == 403


def test_candidates_respect_consent_and_manual_invites_do_not_imply_join(harness):
    aoi,ren = harness.client('aoi'),harness.client('ren')
    request = dict(community_id='peers',tags=['cafe'],desired_count=5)
    result = aoi.write('POST','/circles/candidates',request).json()
    assert {item['user']['id'] for item in result['items']} == {'u-ren','u-mio'}
    assert result['shortage_count'] == 2
    with harness.app.state.database.transaction(True) as conn:
        conn.execute("UPDATE grants SET use_matching=0 WHERE user_id='u-ren' AND community_id='peers'")
    result = aoi.write('POST','/circles/candidates',request).json()
    assert [item['user']['id'] for item in result['items']] == ['u-mio']
    recommended = dict(community_id='peers',title='旅',mode='recommended',tags=['cafe'],desired_count=3,invitee_ids=['u-ren'],client_request_id='stale-candidate')
    assert aoi.write('POST','/circles',recommended).status_code == 409
    created = circle(aoi,invitee_ids=['u-ren'])
    assert created['accepted_count'] == 1 and created['pending_count'] == 1 and created['shortage_count'] == 1
    pid,iid = created['id'],created['invitations'][0]['id']
    for path in ('/circles/'+pid,'/travel-parties/'+pid+'/messages','/circles/'+pid+'/assistant-turns'):
        assert ren.get(path).status_code == 404
    pending = ren.get('/circles').json()['invitations']
    assert pending[0]['id'] == iid
    accepted = ren.write('POST','/circle-invitations/'+iid+'/respond',dict(decision='accepted',version=1,client_request_id='accept'))
    assert accepted.status_code == 200
    assert ren.get('/circles/'+pid).json()['accepted_count'] == 2


def test_invitation_owner_version_cancel_decline_and_idempotency(harness):
    aoi,ren,mio = harness.client('aoi'),harness.client('ren'),harness.client('mio')
    created = circle(aoi,invitee_ids=['u-ren','u-mio'])
    iid = next(i['id'] for i in created['invitations'] if i['invitee']['id']=='u-ren')
    action = dict(decision='accepted',version=1,client_request_id='accept-ren')
    assert mio.write('POST','/circle-invitations/'+iid+'/respond',action).status_code == 404
    assert aoi.write('POST','/circle-invitations/'+iid+'/cancel',dict(version=1,client_request_id='cancel-ren')).status_code == 200
    assert ren.write('POST','/circle-invitations/'+iid+'/respond',action).status_code == 409
    mio_iid = next(i['id'] for i in created['invitations'] if i['invitee']['id']=='u-mio')
    decline = dict(decision='declined',version=1,client_request_id='decline')
    assert mio.write('POST','/circle-invitations/'+mio_iid+'/respond',decline).json()['status'] == 'declined'
    assert mio.write('POST','/circle-invitations/'+mio_iid+'/respond',decline).status_code == 200
    stale = dict(invitee_ids=['u-ren'],version=created['version'],client_request_id='reinvite')
    assert aoi.write('POST','/circles/'+created['id']+'/invitations',stale).status_code == 409
    stale['version'] = aoi.get('/circles/'+created['id']).json()['version']
    fresh = aoi.write('POST','/circles/'+created['id']+'/invitations',stale)
    assert fresh.status_code == 200 and fresh.json()['invitations'][0]['id'] != iid


def test_accept_cancel_race_has_only_one_winner(harness):
    aoi = harness.client('aoi')
    created = circle(aoi,invitee_ids=['u-ren'])
    iid = created['invitations'][0]['id']
    service = Circles(harness.app.state.database)
    def act(cancel):
        try:
            data = dict(version=1,client_request_id='cancel' if cancel else 'accept')
            if not cancel:
                data['decision']='accepted'
            return service.respond('u-aoi' if cancel else 'u-ren',iid,data,cancel)['status']
        except HTTPException as exc:
            return exc.status_code
    with ThreadPoolExecutor(max_workers=2) as pool:
        results = list(pool.map(act,(False,True)))
    assert 409 in results and len(set(results)&{'accepted','cancelled'}) == 1
    with harness.app.state.database.transaction() as conn:
        count = conn.execute("SELECT COUNT(*) FROM travel_party_members WHERE party_id=? AND user_id='u-ren'",(created['id'],)).fetchone()[0]
    assert count == int('accepted' in results)


def test_multiple_turns_use_real_catalog_and_unresolved_numbers_stay_missing(harness):
    aoi = harness.client('aoi')
    pid = circle(aoi)['id']
    def turn(body,key):
        response = aoi.write('POST','/circles/'+pid+'/assistant-turns',dict(body=body,client_request_id=key))
        assert response.status_code == 200,response.text
        return response.json()
    first = turn('6人で森とカフェに行きたい','first')
    assert first['proposed_conditions']['planned_people'] == 6 and first['candidates'] == []
    second = turn('2泊で1人3万円、プラン部分。2027年3月1日','second')
    assert second['proposed_conditions']['budget_yen'] == 30000
    assert [item['plan']['id'] for item in second['candidates']] == ['forest-six']
    assert aoi.get('/circles/'+pid).json()['requirements'] is None
    third = turn('6人か8人で考えています','third')
    assert 'planned_people' not in third['proposed_conditions'] and third['ambiguities']
    fourth = turn('カフェに寄りたい','fourth')
    assert '人数' in fourth['missing_fields'] and fourth['candidates'] == []
    assert turn('6人です','fifth')['candidates']
    negated = turn('仮に30人なら','sixth')
    assert 'planned_people' not in negated['proposed_conditions']
    assert len(aoi.get('/circles/'+pid+'/assistant-turns').json()['items']) == 6
    assert turn('仮に30人なら','sixth')['id'] == negated['id']


def test_provider_pending_has_no_consultation_and_no_private_access(harness):
    aoi,forest,shore = harness.client('aoi'),harness.client('forest'),harness.client('shore')
    pid = circle(aoi)['id']
    requirements(aoi,pid)
    aoi.write('POST','/travel-parties/'+pid+'/messages',dict(body='PRIVATE-INNER-TEXT',client_request_id='inner'))
    aoi.write('POST','/circles/'+pid+'/assistant-turns',dict(body='PRIVATE-ASSISTANT-TEXT',client_request_id='ai'))
    invitation,_ = provider_invite(aoi,pid)
    assert invitation['consultation_id'] is None
    listing = forest.get('/circle-provider-invitations').json()
    assert len(listing['items']) == 1 and 'PRIVATE-' not in json.dumps(listing)
    assert shore.get('/circle-provider-invitations').json()['items'] == []
    assert forest.get('/consultations').json()['items'] == []
    for path in ('/circles/'+pid,'/travel-parties/'+pid+'/messages','/circles/'+pid+'/assistant-turns','/circle-provider-invitations/'+invitation['id']+'/room'):
        assert forest.get(path).status_code == 404
    assert forest.write('POST','/circle-provider-invitations/'+invitation['id']+'/messages',dict(body='早すぎる返信',client_request_id='early')).status_code == 404
    direct = dict(plan_id='forest-six',plan_version=1,requirements_version=1,share_note='',sharing_confirmed=True,client_request_id='bypass')
    assert aoi.write('POST','/travel-parties/'+pid+'/selections',direct).status_code == 409
    assert shore.write('POST','/circle-provider-invitations/'+invitation['id']+'/respond',dict(decision='accepted',version=1,client_request_id='wrong-provider')).status_code == 404


def test_provider_accept_rechecks_exact_shared_conditions(harness):
    aoi,forest = harness.client('aoi'),harness.client('forest')
    pid = circle(aoi)['id']
    requirements(aoi,pid)
    invitation,_ = provider_invite(aoi,pid)
    requirements(aoi,pid,planned_people=7,version=1)
    assert forest.write('POST','/circle-provider-invitations/'+invitation['id']+'/respond',dict(decision='accepted',version=1,client_request_id='stale-accept')).status_code == 409
    assert forest.get('/consultations').json()['items'] == []


def test_legacy_party_cannot_bypass_new_invitation_at_any_state(harness):
    aoi,forest = harness.client('aoi'),harness.client('forest')
    legacy = aoi.write('POST','/communities/peers/travel-parties',dict(title='既存の旅',ko_group_id=None,member_ids=[])).json()
    pid = legacy['id']
    requirements(aoi,pid)
    invitation,_ = provider_invite(aoi,pid)
    direct = dict(plan_id='forest-six',plan_version=1,requirements_version=1,share_note='',sharing_confirmed=True,client_request_id='bypass')
    assert aoi.write('POST','/travel-parties/'+pid+'/selections',direct).status_code == 409
    accepted = accept_provider(forest,invitation)
    assert aoi.write('POST','/travel-parties/'+pid+'/selections',direct).status_code == 409
    assert aoi.write('POST','/circle-provider-invitations/'+invitation['id']+'/cancel',dict(version=accepted['version'],client_request_id='cancel')).status_code == 200
    assert aoi.write('POST','/travel-parties/'+pid+'/selections',direct).status_code == 409


def test_shared_exchange_cancel_reinvite_isolated_and_legacy_guards(harness):
    aoi,forest,created,invitation = setup_shared(harness)
    iid = invitation['id']
    action = dict(decision='accepted',version=1,client_request_id='provider-accept')
    assert forest.write('POST','/circle-provider-invitations/'+iid+'/respond',action).json()['consultation_id'] == invitation['consultation_id']
    assert forest.write('POST','/circle-provider-invitations/'+iid+'/messages',dict(body='SHARED-OLD-REPLY',client_request_id='reply')).status_code == 200
    assert aoi.get('/circle-provider-invitations/'+iid+'/room').json()['messages'][0]['body'] == 'SHARED-OLD-REPLY'
    assert forest.get('/consultations/'+invitation['consultation_id']+'/messages').status_code == 200
    assert forest.write('POST','/consultations/'+invitation['consultation_id']+'/close',dict(version=1)).status_code == 409
    assert aoi.write('POST','/circle-provider-invitations/'+iid+'/cancel',dict(version=2,client_request_id='cancel')).status_code == 200
    assert forest.get('/circle-provider-invitations/'+iid+'/room').status_code == 404
    assert forest.get('/consultations/'+invitation['consultation_id']).status_code == 404
    assert forest.write('POST','/consultations/'+invitation['consultation_id']+'/messages',dict(body='late',client_request_id='late')).status_code == 404
    second,_ = provider_invite(aoi,created['id'],'second-invite')
    second = accept_provider(forest,second,'second-accept')
    assert second['consultation_id'] != invitation['consultation_id']
    assert forest.get('/circle-provider-invitations/'+second['id']+'/room').json()['messages'] == []


def test_proposal_both_confirm_exact_revision_and_revision_clears_confirmations(harness):
    aoi,forest,_,invitation = setup_shared(harness,True)
    ren,shore = harness.client('ren'),harness.client('shore')
    base = '/circle-provider-invitations/'+invitation['id']
    assert aoi.write('POST',base+'/proposals',proposal_data()).status_code == 404
    proposal = forest.write('POST',base+'/proposals',proposal_data())
    assert proposal.status_code == 200,proposal.text
    quote = proposal.json()
    confirm = dict(proposal_id=quote['id'],version=1,client_request_id='confirm')
    assert ren.write('POST',base+'/confirmations',confirm).status_code == 404
    assert shore.write('POST',base+'/confirmations',confirm).status_code == 404
    first = forest.write('POST',base+'/confirmations',confirm).json()
    assert first['status'] == 'awaiting_confirmation'
    both = aoi.write('POST',base+'/confirmations',confirm).json()
    assert both['status'] == 'both_confirmed' and both['reservation_status'] == 'not_booked'
    assert {c['user']['id'] for c in both['confirmations']} == {'u-aoi','provider-forest'}
    revised = forest.write('POST',base+'/proposals',proposal_data(1,'revised')).json()
    assert revised['version'] == 2 and revised['confirmations'] == [] and revised['status'] == 'awaiting_confirmation'
    assert aoi.write('POST',base+'/confirmations',confirm).status_code == 409
    assert forest.write('POST',base+'/proposals',proposal_data(0,'stale')).status_code == 409
    assert aoi.get(base+'/room').json()['proposal']['id'] == revised['id']


def test_exit_and_legacy_party_close_revoke_new_room(harness):
    aoi,forest,created,invitation = setup_shared(harness,True)
    ren = harness.client('ren')
    pid,base = created['id'],'/circle-provider-invitations/'+invitation['id']
    assert ren.get(base+'/room').status_code == 200
    assert ren.write('POST','/communities/peers/leave').status_code == 200
    assert ren.get('/travel-parties/'+pid+'/messages').status_code == 404
    assert ren.get(base+'/room').status_code == 404
    ren.write('POST','/communities/join',dict(invite_code='KO-PEERS-2026'))
    assert ren.get('/circles/'+pid).status_code == 404
    assert aoi.write('POST','/travel-parties/'+pid+'/close').status_code == 200
    assert forest.get(base+'/room').status_code == 404
    assert forest.get('/consultations/'+invitation['consultation_id']).status_code == 404


def test_existing_group_subset_remains_reachable(harness):
    aoi,ren,mio = harness.client('aoi'),harness.client('ren'),harness.client('mio')
    proposed = aoi.write('POST','/communities/peers/proposals',dict(purpose='森の旅',tags=['mountain','cafe'],size=3,trip_id='karuizawa',date='2027-03-01')).json()
    for client in (aoi,ren,mio):
        # Proposal responses use an optimistic version that changes after each response.
        with harness.app.state.database.transaction() as conn:
            version = conn.execute('SELECT version FROM proposals WHERE id=?',(proposed['id'],)).fetchone()[0]
        response = client.write('POST','/proposals/'+proposed['id']+'/respond',dict(decision='accepted',version=version))
        assert response.status_code == 200,response.text
    with harness.app.state.database.transaction() as conn:
        gid = conn.execute('SELECT group_id FROM proposals WHERE id=?',(proposed['id'],)).fetchone()[0]
    subset = aoi.write('POST','/communities/peers/travel-parties',dict(title='代表だけの旧計画',ko_group_id=gid,member_ids=[])).json()
    groups = ren.get('/circles').json()['groups']
    assert groups[0]['circle_id'] is None
    linked = ren.write('POST','/circles/from-group',dict(group_id=gid,client_request_id='connect'))
    assert linked.status_code == 200,linked.text
    assert linked.json()['id'] != subset['id'] and linked.json()['accepted_count'] == 3


def test_schema4_preserves_all_prior_tables_and_rolls_back(tmp_path,monkeypatch):
    from app.circles import schema
    db = Database(tmp_path/'old.db')
    db.initialize(); marketplace_migrate(db); journal_migrate(db)
    with db.transaction(True) as conn:
        conn.execute("INSERT INTO media(id,user_id,storage_key,width,height,sha256,created_at) VALUES('persist-media','u-aoi','persist.jpg',60,40,'hash','2026-01-01')")
        conn.execute("INSERT INTO journal_location_candidates VALUES('persist-media',35.123,136.123,'2026-01-01')")
        conn.execute("INSERT INTO journal_journeys VALUES('persist-journey','u-aoi','以前の旅',1,'2026-01-01')")
        conn.execute("INSERT INTO journal_visits VALUES('persist-visit','u-aoi','persist-journey','23','2026-01-01','保持する場所',35.123,136.123,'persist-media','exif','private',NULL,1,'2026-01-01','2026-01-01')")
        conn.execute("INSERT INTO journal_profiles VALUES('u-aoi',1,2)")
        conn.execute("INSERT INTO travel_parties VALUES('persist-party','peers',NULL,'u-aoi','以前の計画','open','2026-01-01')")
        conn.execute("INSERT INTO travel_party_members VALUES('persist-party','u-aoi')")
    with db.transaction() as conn:
        names = [row[0] for row in conn.execute("SELECT name FROM sqlite_master WHERE type='table'")]
        before = {name:[tuple(row) for row in conn.execute('SELECT * FROM "'+name+'" ORDER BY rowid')] for name in names}
    valid = schema.DDL
    monkeypatch.setattr(schema,'DDL',valid+('INVALID SQL',))
    with pytest.raises(Exception):
        migrate(db)
    with db.transaction() as conn:
        assert conn.execute('PRAGMA user_version').fetchone()[0] == 3
        assert not conn.execute("SELECT name FROM sqlite_master WHERE name LIKE 'circle_%'").fetchall()
    monkeypatch.setattr(schema,'DDL',valid)
    migrate(db)
    db.initialize(); marketplace_migrate(db); journal_migrate(db); migrate(db)
    with db.transaction() as conn:
        after = {name:[tuple(row) for row in conn.execute('SELECT * FROM "'+name+'" ORDER BY rowid')] for name in names}
        assert before == after
        assert conn.execute('PRAGMA user_version').fetchone()[0] == 4
        assert conn.execute("SELECT mode FROM circle_rooms WHERE party_id='persist-party'").fetchone()[0] == 'legacy'
        assert not conn.execute('PRAGMA foreign_key_check').fetchall()


def test_cache_exception_only_for_public_hash_image(tmp_path):
    from app.config import Settings
    from app.main import create_app
    from conftest import Client
    static = tmp_path/'static'
    static.mkdir()
    name = 'welcome-woodland-97a0e1c711d0.webp'
    (static/name).write_bytes(b'public-bundled-art')
    (static/'other.webp').write_bytes(b'other')
    settings = Settings(db_path=tmp_path/'cache.db',media_dir=tmp_path/'media',model_dir=tmp_path/'no-model',static_dir=static,worker_enabled=False)
    app = create_app(settings)
    with asyncio.Runner() as runner:
        lifecycle = app.router.lifespan_context(app)
        runner.run(lifecycle.__aenter__())
        client = Client(runner,app)
        try:
            public = client.request('GET','/../'+name)
            assert public.status_code == 200 and public.headers['cache-control'] == 'public, max-age=86400, immutable'
            assert client.request('GET','/../other.webp').headers['cache-control'] == 'no-store'
            assert client.get('/bootstrap').headers['cache-control'] == 'no-store'
            assert client.get('/media/not-found').headers['cache-control'] == 'no-store'
            (static/name).unlink()
            assert client.request('GET','/../'+name).headers['cache-control'] == 'no-store'
        finally:
            client.close()
            runner.run(lifecycle.__aexit__(None,None,None))
