import io
from concurrent.futures import ThreadPoolExecutor
from datetime import date, timedelta
import json

from PIL import Image, TiffImagePlugin
import pytest

from app.database import Database
from app.journal.schema import migrate
from app.journal.service import JournalService
from app.marketplace.schema import migrate as marketplace_migrate


def journey(client, key='trip-one'):
    response = client.write('POST', '/journal/journeys', {'title': '東海の休日', 'request_key': key})
    assert response.status_code == 200, response.text
    return response.json()


def visit_data(jid, prefecture='23', **overrides):
    return dict(journey_id=jid, prefecture_id=prefecture, visited_on='2026-01-01', place_label='訪問した公園',
                latitude=None, longitude=None, media_id=None, source='manual', visibility='private',
                community_id=None, confirmed=True, request_key='visit-'+prefecture, **overrides)


def payload(jid, prefecture='23', **overrides):
    result = visit_data(jid, prefecture)
    result.update(overrides)
    return result


def add(client, jid, prefecture='23', **overrides):
    response = client.write('POST', '/journal/visits', payload(jid, prefecture, **overrides))
    assert response.status_code == 200, response.text
    return response.json()


def edit_data(item, **overrides):
    fields = ('journey_id','prefecture_id','visited_on','place_label','latitude','longitude','media_id',
              'source','visibility','community_id','confirmed','version')
    result = {key:item[key] for key in fields}
    result.update(overrides)
    return result


def gps_photo(reference='N', latitude=(35,10,0), longitude=(136,50,0)):
    image = Image.new('RGB', (60,40), (80,120,50))
    exif = Image.Exif()
    exif[270] = 'private-device-note'
    exif[34853] = {1:reference, 2:tuple(TiffImagePlugin.IFDRational(n) for n in latitude),
                   3:'E', 4:tuple(TiffImagePlugin.IFDRational(n) for n in longitude)}
    out = io.BytesIO()
    image.save(out, format='JPEG', exif=exif)
    return out.getvalue()


def upload(client, opt_in=True, raw=None):
    response = client.request('POST', '/media' + ('?read_location=true' if opt_in else ''),
                              files={'file': ('photo.jpg', raw or gps_photo(), 'image/jpeg')})
    assert response.status_code == 200, response.text
    return response.json()


def profile(client, target='u-aoi'):
    response = client.get('/journal/profile/' + target)
    assert response.status_code == 200, response.text
    return response.json()


def test_explicit_gps_opt_in_owner_only_and_clean_image(harness):
    aoi, ren = harness.client('aoi'), harness.client('ren')
    ignored = upload(aoi, False)
    assert ignored['location_candidate'] is None
    photo = upload(aoi)
    assert photo['location_candidate'] == {'latitude':35.1666667,'longitude':136.8333333}
    response = aoi.get('/media/' + photo['id'])
    assert not Image.open(io.BytesIO(response.content)).getexif()
    assert ren.get('/journal/media/'+photo['id']+'/location-candidate').status_code == 404
    assert aoi.get('/journal/media/'+photo['id']+'/location-candidate').json()['location_candidate'] == photo['location_candidate']
    assert all(item['id'] != photo['id'] for item in ren.get('/journal/media').json()['items'])
    assert 'private-device-note' not in json.dumps(aoi.get('/journal/media').json())
    draft = aoi.write('POST', '/posts', dict(community_id='peers', media_ids=[photo['id']], tags=[])).json()
    aoi.write('PATCH', '/posts/'+draft['id'], {'status':'published'})
    assert 'location_candidate' not in json.dumps(ren.get('/communities/peers/feed').json())


@pytest.mark.parametrize('reference,latitude', [('X',(35,0,0)), ('N',(91,0,0)), ('N',(35,60,0)), ('N',(35,0,60))])
def test_malformed_gps_is_not_a_candidate(harness, reference, latitude):
    aoi = harness.client('aoi')
    assert upload(aoi, raw=gps_photo(reference,latitude))['location_candidate'] is None


def test_badge_uses_unique_confirmed_visits_and_recalculates(harness):
    aoi = harness.client('aoi')
    jid = journey(aoi)['id']
    assert profile(aoi)['badges'][0]['achieved_count'] == 0
    visits = [add(aoi, jid, prefecture) for prefecture in ('23','21','24','22')]
    duplicate = add(aoi, jid, '23', request_key='same-pref-another-day', visited_on='2026-01-02')
    badge = profile(aoi)['badges'][0]
    assert badge['earned'] and badge['achieved_count'] == 4 and badge['remaining_prefecture_ids'] == []
    updated = aoi.write('PUT', '/journal/visits/'+visits[-1]['id'], edit_data(visits[-1], prefecture_id='20'))
    assert updated.status_code == 200
    badge = profile(aoi)['badges'][0]
    assert not badge['earned'] and badge['achieved_count'] == 3 and badge['remaining_prefecture_ids'] == ['22']
    assert aoi.write('DELETE', '/journal/visits/'+visits[0]['id'], {'version':1}).status_code == 200
    assert profile(aoi)['badges'][0]['achieved_count'] == 3
    assert aoi.write('DELETE', '/journal/visits/'+duplicate['id'], {'version':1}).status_code == 200
    assert profile(aoi)['badges'][0]['achieved_count'] == 2


def test_achievements_and_visit_sharing_are_separate_and_coarse(harness):
    aoi, ren, provider = harness.client('aoi'), harness.client('ren'), harness.client('forest')
    jid = journey(aoi)['id']
    private = add(aoi, jid, latitude=35.1234567, longitude=136.1234567, place_label='非公開の訪問先')
    assert not profile(ren)['visited_prefectures'] and not profile(ren)['shared_visits']
    assert aoi.write('PUT','/journal/profile',{'share_achievements':True,'version':1}).status_code == 200
    shared_profile = profile(ren)
    assert shared_profile['visited_prefectures'][0]['id'] == '23'
    assert shared_profile['shared_visits'] == [] and '35.1234567' not in json.dumps(shared_profile)
    assert provider.get('/journal/profile/u-aoi').status_code == 404
    shared = aoi.write('PUT','/journal/visits/'+private['id'], edit_data(private,visibility='community',community_id='peers')).json()
    public_visit = profile(ren)['shared_visits'][0]
    assert public_visit['latitude'] is None and public_visit['longitude'] is None
    assert public_visit['media_id'] is None and public_visit['journey_id'] is None
    assert aoi.write('PUT','/journal/profile',{'share_achievements':False,'version':2}).status_code == 200
    assert profile(ren)['badges'] == [] and len(profile(ren)['shared_visits']) == 1
    assert aoi.get('/journal/journeys/'+jid).json()['visits'][0]['latitude'] == 35.1234567
    assert ren.get('/journal/journeys/'+jid).status_code == 404
    assert ren.write('PUT','/journal/visits/'+shared['id'],edit_data(shared)).status_code == 404
    assert ren.write('DELETE','/journal/visits/'+shared['id'],{'version':2}).status_code == 404


def test_shared_photo_keeps_post_audience_and_retracts_on_delete(harness):
    aoi, ren = harness.client('aoi'), harness.client('ren')
    jid = journey(aoi)['id']
    photo = upload(aoi)
    visit = add(aoi,jid, media_id=photo['id'], source='exif', **photo['location_candidate'], visibility='community',community_id='peers')
    assert profile(ren)['shared_visits'][0]['media_url'] is None
    draft = aoi.write('POST','/posts',dict(community_id='peers',media_ids=[photo['id']],tags=[])).json()
    aoi.write('PATCH','/posts/'+draft['id'],{'status':'published'})
    assert profile(ren)['shared_visits'][0]['media_url'] == '/api/media/'+photo['id']
    aoi.write('PATCH','/posts/'+draft['id'],{'status':'draft'})
    assert profile(ren)['shared_visits'][0]['media_url'] is None
    assert aoi.write('DELETE','/posts/'+draft['id']).status_code == 200
    assert profile(aoi)['badges'][0]['achieved_count'] == 0
    assert aoi.get('/journal/journeys/'+jid).json()['visits'] == []
    assert aoi.get('/journal/media/'+photo['id']+'/location-candidate').status_code == 404


def test_exif_claim_requires_owned_candidate_and_matching_coordinates(harness):
    aoi, ren = harness.client('aoi'), harness.client('ren')
    jid, other_jid = journey(aoi)['id'], journey(ren)['id']
    photo = upload(aoi)
    valid = payload(jid, media_id=photo['id'], source='exif', **photo['location_candidate'])
    assert aoi.write('POST','/journal/visits',valid | {'latitude':36}).status_code == 422
    assert ren.write('POST','/journal/visits',valid | {'journey_id':other_jid}).status_code == 404
    no_gps = upload(aoi,False)
    assert aoi.write('POST','/journal/visits',valid | {'media_id':no_gps['id']}).status_code == 422
    saved = aoi.write('POST','/journal/visits',valid)
    assert saved.status_code == 200
    assert aoi.write('POST','/journal/visits',valid | {'request_key':'duplicate-photo'}).status_code == 409
    assert aoi.write('DELETE','/journal/media/'+photo['id']+'/location-candidate').status_code == 200
    assert aoi.get('/journal/media/'+photo['id']+'/location-candidate').json()['location_candidate'] is None
    # Discarding an unconfirmed candidate does not retract an already confirmed visit.
    assert len(aoi.get('/journal/journeys/'+jid).json()['visits']) == 1
    retained = aoi.write('PUT','/journal/visits/'+saved.json()['id'],edit_data(saved.json(),place_label='場所名を訂正'))
    assert retained.status_code == 200 and retained.json()['source'] == 'exif'
    assert aoi.write('PUT','/journal/visits/'+saved.json()['id'],edit_data(retained.json(),latitude=36)).status_code == 422


def test_payload_validation_conflicts_and_non_owner_journey(harness):
    aoi, ren = harness.client('aoi'), harness.client('ren')
    jid = journey(aoi)['id']
    for overrides in ({'confirmed':False},{'visited_on':str(date.today()+timedelta(days=10))},
                      {'latitude':100,'longitude':0},{'latitude':35},{'prefecture_id':'99'},
                      {'visibility':'community'},{'community_id':'peers'},{'owner':'u-ren'}):
        assert aoi.write('POST','/journal/visits',payload(jid,**overrides)).status_code == 422
    assert ren.write('POST','/journal/visits',payload(jid)).status_code == 404
    for nonfinite in ('NaN', 'Infinity', '-Infinity'):
        raw = json.dumps(payload(jid,longitude=136))
        raw = raw.replace('"latitude": null', '"latitude": '+nonfinite)
        assert aoi.request('POST','/journal/visits',content=raw,headers={'Content-Type':'application/json'}).status_code == 422
    item = add(aoi,jid)
    updated = aoi.write('PUT','/journal/visits/'+item['id'],edit_data(item,place_label='新しい場所')).json()
    assert updated['version'] == 2
    assert aoi.write('PUT','/journal/visits/'+item['id'],edit_data(item)).status_code == 409
    assert aoi.write('DELETE','/journal/visits/'+item['id'],{'version':1}).status_code == 409
    assert aoi.write('PUT','/journal/profile',{'share_achievements':True,'version':1}).status_code == 200
    assert aoi.write('PUT','/journal/profile',{'share_achievements':False,'version':1}).status_code == 409


def test_idempotency_survives_concurrency_and_deleted_key_does_not_resurrect(harness):
    aoi = harness.client('aoi')
    jid = journey(aoi)['id']
    service = JournalService(harness.app.state.database)
    data = payload(jid)
    with ThreadPoolExecutor(max_workers=2) as pool:
        results = list(pool.map(lambda _:service.create_visit('u-aoi',data), range(2)))
    assert results[0]['id'] == results[1]['id']
    assert len(aoi.get('/journal/journeys/'+jid).json()['visits']) == 1
    assert aoi.write('POST','/journal/visits',data | {'place_label':'別の場所'}).status_code == 409
    assert aoi.write('DELETE','/journal/visits/'+results[0]['id'],{'version':1}).status_code == 200
    assert aoi.write('POST','/journal/visits',data).status_code == 409
    assert aoi.write('DELETE','/journal/journeys/'+jid,{'version':1}).status_code == 409
    version = aoi.get('/journal/journeys/'+jid).json()['journey']['version']
    assert aoi.write('DELETE','/journal/journeys/'+jid,{'version':version}).status_code == 200
    assert aoi.write('POST','/journal/journeys',{'title':'東海の休日','request_key':'trip-one'}).status_code == 409


def test_leaving_revokes_visit_share_and_join_does_not_restore(harness):
    ren, aoi = harness.client('ren'), harness.client('aoi')
    jid = journey(ren)['id']
    add(ren,jid,visibility='community',community_id='peers')
    assert len(profile(aoi,'u-ren')['shared_visits']) == 1
    assert ren.write('POST','/communities/peers/leave').status_code == 200
    assert aoi.get('/journal/profile/u-ren').status_code == 404
    assert ren.write('POST','/communities/join',{'invite_code':'KO-PEERS-2026'}).status_code == 200
    assert profile(aoi,'u-ren')['shared_visits'] == []
    visit = ren.get('/journal/journeys/'+jid).json()['visits'][0]
    assert visit['visibility'] == 'private' and visit['community_id'] is None and visit['version'] == 2


def test_schema3_is_additive_and_reopen_preserves_records(harness):
    aoi = harness.client('aoi')
    jid = journey(aoi)['id']
    add(aoi,jid)
    db = harness.app.state.database
    with db.transaction() as conn:
        expected_users = [tuple(row) for row in conn.execute('SELECT * FROM users ORDER BY id')]
        expected_posts = [tuple(row) for row in conn.execute('SELECT * FROM posts ORDER BY id')]
    reopened = Database(harness.settings.db_path)
    reopened.initialize()
    marketplace_migrate(reopened)
    migrate(reopened)
    with reopened.transaction() as conn:
        assert conn.execute('PRAGMA user_version').fetchone()[0] == 12
        assert expected_users == [tuple(row) for row in conn.execute('SELECT * FROM users ORDER BY id')]
        assert expected_posts == [tuple(row) for row in conn.execute('SELECT * FROM posts ORDER BY id')]
        assert not conn.execute('PRAGMA foreign_key_check').fetchall()
    assert JournalService(reopened).profile('u-aoi')['badges'][0]['achieved_count'] == 1


def test_migration_rolls_back_whole_change(tmp_path, monkeypatch):
    from app.journal import schema
    db = Database(tmp_path / 'migration.db')
    db.initialize()
    marketplace_migrate(db)
    with db.transaction() as conn:
        before = [tuple(row) for row in conn.execute('SELECT * FROM users ORDER BY id')]
    monkeypatch.setattr(schema, 'DDL', schema.DDL + ('THIS IS NOT SQL',))
    with pytest.raises(Exception):
        schema.migrate(db)
    with db.transaction() as conn:
        assert conn.execute('PRAGMA user_version').fetchone()[0] == 2
        assert conn.execute("SELECT COUNT(*) FROM sqlite_master WHERE name LIKE 'journal_%'").fetchone()[0] == 0
        assert before == [tuple(row) for row in conn.execute('SELECT * FROM users ORDER BY id')]


def test_schema2_migration_preserves_every_existing_table(tmp_path):
    db = Database(tmp_path / 'existing.db')
    db.initialize()
    marketplace_migrate(db)
    with db.transaction(True) as conn:
        conn.execute("INSERT INTO media(id,user_id,storage_key,width,height,sha256,created_at) VALUES('old-photo','u-aoi','old-photo.jpg',60,40,'hash','2026-01-01')")
        conn.execute("INSERT INTO posts VALUES('old-post','u-aoi','peers','以前の旅','[]','published','以前の場所','2026-01-01','2026-01-01')")
        conn.execute("INSERT INTO post_media VALUES('old-post','old-photo',0)")
        tables = [row[0] for row in conn.execute("SELECT name FROM sqlite_master WHERE type='table'")]
        before = {table:[tuple(row) for row in conn.execute('SELECT * FROM "'+table+'" ORDER BY rowid')] for table in tables}
    migrate(db)
    with db.transaction() as conn:
        after = {table:[tuple(row) for row in conn.execute('SELECT * FROM "'+table+'" ORDER BY rowid')] for table in tables}
        assert before == after
        assert conn.execute('PRAGMA user_version').fetchone()[0] == 3
        assert not conn.execute('PRAGMA foreign_key_check').fetchall()


def test_auth_csrf_and_catalog(harness):
    anonymous, aoi = harness.client(), harness.client('aoi')
    assert anonymous.get('/journal/catalog').status_code == 401
    assert len(aoi.get('/journal/catalog').json()['prefectures']) == 47
    assert aoi.write('POST','/journal/journeys',{'title':'旅','request_key':'one'},headers={'X-CSRF-Token':'bad'}).status_code == 403
    assert len(aoi.get('/journal/people?community_id=peers').json()['items']) == 3
    assert harness.client('forest').get('/journal/people?community_id=peers').status_code == 404
