"""Append-only operating content must work through the actual user APIs."""
import hashlib
import json
from datetime import UTC, datetime, timedelta

import pytest
from app import operational_seed
from app.analytics import city_scope
from app.daytrip import service as daytrip_service
from app.enrichment import enrich
from app.marketplace.schemas import ProviderPlanInput
from app.operational_seed import INITIAL, PACK, PREFIX, apply, key
from PIL import Image

NOW = datetime(2026, 11, 10, 3, tzinfo=UTC)


def fingerprint(db):
    """Keep values (including account hashes) out of assertion output."""
    with db.transaction() as conn:
        tables = [row[0] for row in conn.execute("SELECT name FROM sqlite_master WHERE type='table'")]
        return {table: {hashlib.sha256(json.dumps(tuple(row)).encode()).hexdigest()
                       for row in conn.execute('SELECT * FROM "' + table.replace('"', '""') + '"')}
                for table in tables}


@pytest.fixture
def baseline(harness, monkeypatch):
    monkeypatch.setattr(city_scope, 'clock_now', lambda: NOW)
    monkeypatch.setattr(daytrip_service, 'clock_now', lambda: NOW)
    enrich(harness.app.state.database, harness.settings, NOW)
    return harness


def test_pack_preserves_every_existing_row_and_photo_and_is_idempotent(baseline):
    db, settings = baseline.app.state.database, baseline.settings
    with db.transaction(True) as conn:
        conn.execute("INSERT INTO residence_profiles VALUES('u-aoi','27100',0,3,?)", (NOW.isoformat(),))
    prior = fingerprint(db)
    old_photo = settings.media_dir / 'existing-image.jpg'
    old_photo.write_bytes(b'Existing input must remain byte-for-byte unchanged')
    report = apply(db, settings, NOW)
    after = fingerprint(db)
    assert all(prior[table] <= after[table] for table in prior)
    assert old_photo.read_bytes() == b'Existing input must remain byte-for-byte unchanged'
    assert report['completed_outings'] == 140 and report['future_outings'] == 6
    assert report['counts']['users'] == 3 and report['counts']['providers'] == 4
    for table, count in dict(posts=60, media=60, journal_visits=60, journal_journeys=30,
                             daytrip_benefits=12, provider_plans=12, travel_parties=48,
                             daytrip_participants=876, daytrip_ledger=1680).items():
        assert report['counts'][table] == count, table
    repeat = apply(db, settings, NOW + timedelta(days=30))
    assert repeat['already_applied'] and repeat['applied_at'] == report['applied_at']
    assert fingerprint(db) == after
    images = list(settings.media_dir.glob(PREFIX + '*.jpg'))
    assert len(images) == 60
    with Image.open(images[0]) as image:
        assert image.format == 'JPEG' and not image.getexif()
    with db.transaction() as conn:
        assert conn.execute('PRAGMA foreign_key_check').fetchall() == []
        for row in conn.execute("SELECT body FROM provider_plans WHERE id LIKE 'ops26-%'"):
            ProviderPlanInput.model_validate(json.loads(row['body']) | {'status': 'published'})
        assert conn.execute("SELECT COUNT(*) FROM journal_visits WHERE id LIKE 'ops26-%' AND (visibility!='private' OR community_id IS NOT NULL)").fetchone()[0] == 0
        assert conn.execute("SELECT COUNT(*) FROM residence_profiles WHERE user_id LIKE 'ops26-%'").fetchone()[0] == 0
        assert conn.execute("SELECT COUNT(*) FROM consultation_messages m JOIN consultations c ON c.id=m.consultation_id JOIN circle_provider_invitations i ON i.consultation_id=c.id WHERE m.id LIKE 'ops26-%' AND julianday(m.created_at)<julianday(i.accepted_at)").fetchone()[0] == 0
        assert conn.execute("SELECT COUNT(*) FROM daytrip_outings o JOIN circle_provider_invitations i ON i.id=o.invitation_id WHERE o.id LIKE 'ops26-%' AND (julianday(o.created_at)<julianday(i.accepted_at) OR julianday(o.created_at)>=julianday(o.starts_at))").fetchone()[0] == 0
        assert conn.execute("SELECT COUNT(*) FROM daytrip_ledger l JOIN daytrip_outings o ON o.id=l.outing_id WHERE l.id LIKE 'ops26-%' AND julianday(l.created_at)<julianday(o.ends_at)").fetchone()[0] == 0


def test_initial_accounts_have_visible_history_messages_private_map_and_usable_coupons(baseline):
    apply(baseline.app.state.database, baseline.settings, NOW)
    for uid in INITIAL:
        client = baseline.client(uid.removeprefix('u-'))
        me = client.get('/daytrip/me')
        assert me.status_code == 200, me.text
        data = me.json()
        assert data['completed_count'] == 20 and data['rank'] >= 4
        assert data['points'] > 2000 and data['eligible_points'] == data['points']
        assert len([row for row in data['benefits'] if row['id'].startswith(PREFIX)]) == 12
        journeys = client.get('/journal/journeys').json()['items']
        assert len(journeys) == 10 and sum(row['visit_count'] for row in journeys) == 20
        profile = client.get('/journal/profile/' + uid).json()
        assert len(profile['shared_visits']) == 20
        assert all(row['latitude'] is not None and row['visibility'] == 'private' for row in profile['shared_visits'])
        circles = client.get('/circles').json()['items']
        added = [row for row in circles if row['id'].startswith(PREFIX)]
        assert len(added) == 12 and all(row['community_id'] == 'peers' for row in added)
        assert all(row['accepted_count'] == 6 for row in added)
        media = client.get('/media/' + key('media', uid, 6))
        assert media.status_code == 200 and media.headers['content-type'].startswith('image/jpeg')
    aoi, forest = baseline.client('aoi'), baseline.client('forest')
    assert aoi.get('/journal/profile/u-ren').json()['shared_visits'] == []
    circle = key('circle', 'history', 6, 0)
    private = aoi.get('/travel-parties/' + circle + '/messages')
    assert private.status_code == 200 and len(private.json()['items']) >= 4
    assert forest.get('/travel-parties/' + circle + '/messages').status_code == 404
    room = '/circle-provider-invitations/' + key('invite', 'history', 6, 0) + '/room'
    shared = forest.get(room)
    assert shared.status_code == 200, shared.text
    assert '6人で集まって、次の日帰りを相談しましょう。' not in shared.text
    assert '予約はこの会話だけでは確定しません。' in shared.text
    reserve = aoi.write('POST', '/daytrip/benefits/' + key('benefit', 0) + '/reserve',
                       dict(outing_id=key('outing', 'future', 0), client_request_id='operational-coupon-check'))
    assert reserve.status_code == 200, reserve.text
    assert reserve.json()['status'] == 'reserved' and reserve.json()['discount_yen'] == 500
    assert reserve.json()['total_yen'] == 4300
    for days in (30, 90, 365):
        response = forest.get(f'/providers/forest-house/city-analytics?days={days}')
        assert response.status_code == 200, response.text
        city = response.json()
        assert city['provider_count'] == 6 and city['summary']['visitors']['count'] == 42
        assert city['summary']['returning_visitors']['count'] == 42
        assert city['providers']['status'] == 'available'
        assert city['origins']['status'] == 'available' and len(city['origins']['areas']) == 6
        assert city['origins']['missing_visitors'] == 6
        assert all(row['visitors'] == 6 and row['returning_visitors'] == 6 for row in city['origins']['areas'])


def test_missing_manifest_collision_and_mid_apply_failure_rollback(baseline, monkeypatch):
    db = baseline.app.state.database
    before = fingerprint(db)

    def fail(_self):
        raise ValueError('deliberate plan-stage failure')

    with monkeypatch.context() as patch:
        patch.setattr(operational_seed.ContentPack, 'make_plans', fail)
        with pytest.raises(ValueError, match='plan-stage'):
            apply(db, baseline.settings, NOW)
    assert fingerprint(db) == before
    with db.transaction(True) as conn:
        conn.execute("INSERT INTO users VALUES('ops26-existing','existing-account','Preserved','P','#000','','',0)")
    before = fingerprint(db)
    with pytest.raises(ValueError, match='namespace'):
        apply(db, baseline.settings, NOW)
    assert fingerprint(db) == before
    with db.transaction() as conn:
        assert conn.execute('SELECT 1 FROM settings WHERE key=?', (PACK,)).fetchone() is None
