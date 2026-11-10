import json
import sqlite3
from datetime import timedelta

import pytest
from app.enrichment import enrich
from app.marketplace.service import Marketplace
from app.operational_seed import apply as operating_content
from app.programs import schema, service
from app.programs.catalog import PROGRAMS, plan_id
from app.programs.seed import FirstStage
from app.programs.seed import apply as program_content
from test_operational_seed import NOW, fingerprint

PID = 'n-nishi-pottery'
BASE = '/daytrip/programs'
MEMBERS = ['u-aoi'] + [f'extra26-person-{index:03}' for index in range(5)]


@pytest.fixture
def programs(harness, monkeypatch):
    monkeypatch.setattr(service, 'clock_now', lambda: NOW)
    enrich(harness.app.state.database, harness.settings, NOW)
    operating_content(harness.app.state.database, harness.settings, NOW)
    return harness


def find(client, pid=PID):
    response = client.get(BASE)
    assert response.status_code == 200, response.text
    return next(item for item in response.json()['items'] if item['id'] == pid)


class Stage(FirstStage):
    def completed_person(self, oid, uid, witness, points, end, index):
        # Progress must not depend on badges/point amounts; state is the evidence.
        return None


def extra_stage(harness, order, day, *, future=False, same_plan=False):
    db = harness.app.state.database
    with db.transaction(True) as conn:
        builder = Stage(conn, db, harness.settings, NOW)
        definition = PROGRAMS[0]
        sid = definition['steps'][0 if same_plan else order][0]
        row = conn.execute('SELECT * FROM provider_plans WHERE id=?', (plan_id(PID, sid),)).fetchone()
        builder.plans = {0: Marketplace(db).plan_out(conn, row)}
        builder.providers = [(definition['provider_id'], 'provider-forest')]
        room = builder.room(20 + order * 2, 0, MEMBERS, day, future=future)
        return builder.outing(20 + order, MEMBERS, room, day, future=future)


def link(client, sid, oid, version):
    return client.write('PUT', BASE + '/' + PID + '/steps/' + sid, dict(outing_id=oid, version=version))


def test_seed_is_append_only_idempotent_and_only_first_dedicated_stage_is_complete(programs):
    db = programs.app.state.database
    before = fingerprint(db)
    report = program_content(db, programs.settings, NOW)
    after = fingerprint(db)
    assert all(before[table] <= after[table] for table in before)
    assert report['plans'] == 6 and report['programs'] == 2
    assert program_content(db, programs.settings, NOW + timedelta(days=10))['already_applied']
    assert fingerprint(db) == after
    schema.migrate(db)
    assert fingerprint(db) == after
    with db.transaction() as conn:
        assert conn.execute('PRAGMA user_version').fetchone()[0] == 12
        assert conn.execute('PRAGMA foreign_key_check').fetchall() == []
    aoi, ren = programs.client('aoi'), programs.client('ren')
    pottery = find(aoi)
    assert pottery['available'] and pottery['total_price_yen'] == 7800
    assert pottery['enrollment']['completed_count'] == 1
    assert [row['status'] for row in pottery['enrollment']['steps']] == ['completed', 'unplanned', 'unplanned']
    assert find(aoi, 'n-nishi-garden')['enrollment'] is None
    assert find(ren)['enrollment'] is None
    assert programs.client().get(BASE).status_code == 401
    assert len(aoi.get(BASE + '/' + PID + '/outings').json()['items']) == 1
    assert ren.get(BASE + '/' + PID + '/outings').json()['items'] == []


def test_enrollment_replay_csrf_owner_scope_and_cancellation_preserve_attendance(programs):
    db = programs.app.state.database
    program_content(db, programs.settings, NOW)
    aoi, ren, forest = programs.client('aoi'), programs.client('ren'), programs.client('forest')
    path = BASE + '/' + PID + '/enroll'
    assert ren.write('POST', path, dict(client_request_id='enroll-1', user_id='u-aoi')).status_code == 422
    assert ren.write('POST', path, dict(client_request_id='enroll-1'), headers={'X-CSRF-Token': 'wrong'}).status_code == 403
    one = ren.write('POST', path, dict(client_request_id='enroll-1'))
    assert one.status_code == 200 and one.json()['completed_count'] == 0
    assert ren.write('POST', path, dict(client_request_id='enroll-1')).json() == one.json()
    oid = find(aoi)['enrollment']['steps'][0]['outing_id']
    assert link(ren, 'shape', oid, 1).status_code == 404
    assert forest.write('POST', path, dict(client_request_id='staff-own')).status_code == 200
    assert link(forest, 'shape', oid, 1).status_code == 404
    with db.transaction() as conn:
        before = tuple(conn.execute('SELECT COUNT(*),SUM(points) FROM daytrip_ledger').fetchone())
    cancelled = aoi.write('POST', BASE + '/' + PID + '/cancel', dict(version=1, client_request_id='cancel-1'))
    assert cancelled.status_code == 200 and cancelled.json()['status'] == 'cancelled'
    assert aoi.write('POST', BASE + '/' + PID + '/cancel', dict(version=1, client_request_id='cancel-1')).json() == cancelled.json()
    assert link(aoi, 'shape', oid, 1).status_code == 409
    enrolled = aoi.write('POST', path, dict(client_request_id='enroll-again')).json()
    assert enrolled['version'] == 3 and enrolled['completed_count'] == 0
    with db.transaction() as conn:
        assert tuple(conn.execute('SELECT COUNT(*),SUM(points) FROM daytrip_ledger').fetchone()) == before


def test_sequence_same_jst_day_wrong_plan_and_correction_recompute_all_steps(programs):
    db = programs.app.state.database
    program_content(db, programs.settings, NOW)
    aoi = programs.client('aoi')
    first = aoi.get(BASE + '/' + PID + '/outings').json()['items'][0]
    first_day = service.datetime.fromisoformat(first['ends_at']).astimezone(service.JST).date()
    second = extra_stage(programs, 1, first_day)
    assert link(aoi, 'decorate', second, 1).status_code == 409
    assert link(aoi, 'decorate', first['id'], 1).status_code == 404
    with db.transaction(True) as conn:
        conn.execute('UPDATE daytrip_outings SET starts_at=?,ends_at=? WHERE id=?',
                     ((NOW - timedelta(days=2, hours=3)).isoformat(), (NOW - timedelta(days=2)).isoformat(), second))
    two = link(aoi, 'decorate', second, 1)
    assert two.status_code == 200, two.text
    assert two.json()['completed_count'] == 2
    third = extra_stage(programs, 2, NOW.date() - timedelta(days=1))
    three = link(aoi, 'receive', third, 2)
    assert three.status_code == 200 and three.json()['status'] == 'completed'
    assert link(aoi, 'receive', None, 2).status_code == 409
    with db.transaction(True) as conn:
        conn.execute("UPDATE daytrip_participants SET provider_verified=0 WHERE outing_id=? AND user_id='u-aoi'", (first['id'],))
    progress = find(aoi)['enrollment']
    assert progress['completed_count'] == 0
    assert all(step['status'] == 'awaiting_confirmation' for step in progress['steps'])
    with db.transaction(True) as conn:
        conn.execute("UPDATE daytrip_participants SET provider_verified=1,full_route=0 WHERE outing_id=? AND user_id='u-aoi'", (first['id'],))
    assert find(aoi)['enrollment']['completed_count'] == 0
    with db.transaction(True) as conn:
        conn.execute("UPDATE daytrip_participants SET full_route=1 WHERE outing_id=? AND user_id='u-aoi'", (first['id'],))
        conn.execute('UPDATE daytrip_participants SET revoked=1 WHERE outing_id=? AND user_id=?', (first['id'], MEMBERS[1]))
    assert find(aoi)['enrollment']['completed_count'] == 0


def test_future_and_unshared_outings_never_complete_and_private_snapshot_stays_manageable(programs):
    db = programs.app.state.database
    program_content(db, programs.settings, NOW)
    aoi, ren = programs.client('aoi'), programs.client('ren')
    future = extra_stage(programs, 1, NOW.date() + timedelta(days=7), future=True)
    assert link(aoi, 'decorate', future, 1).json()['steps'][1]['status'] == 'planned'
    with db.transaction(True) as conn:
        conn.execute("UPDATE provider_plans SET status='draft',body=json_set(body,'$.title','PRIVATE-EDIT-NEVER-SHARE') WHERE id=?", (plan_id(PID, 'shape'),))
    own = find(aoi)
    assert not own['available'] and '登録時' in own['price_note']
    assert 'PRIVATE-EDIT-NEVER-SHARE' not in json.dumps(own, ensure_ascii=False)
    assert PID not in [item['id'] for item in ren.get(BASE).json()['items']]
    assert aoi.get(BASE + '/' + PID + '/outings').status_code == 404
    assert link(aoi, 'decorate', None, 2).status_code == 200
    cancelled = aoi.write('POST', BASE + '/' + PID + '/cancel', dict(version=3, client_request_id='closed-cancel'))
    assert cancelled.status_code == 200 and cancelled.json()['status'] == 'cancelled'
    assert aoi.write('POST', BASE + '/' + PID + '/enroll', dict(client_request_id='closed-enroll')).status_code == 404


def test_migration_failure_rolls_back_only_new_tables(tmp_path, monkeypatch):
    from app.database import Database
    db = Database(tmp_path / 'migration.db')
    with db.transaction(True) as conn:
        conn.execute('CREATE TABLE users(id TEXT PRIMARY KEY)')
        conn.execute('CREATE TABLE daytrip_outings(id TEXT PRIMARY KEY)')
        conn.execute("INSERT INTO users VALUES('preserved')")
        conn.execute('PRAGMA user_version=11')
    monkeypatch.setattr(schema, 'DDL', schema.DDL + ('INVALID SQL',))
    with pytest.raises(sqlite3.OperationalError):
        schema.migrate(db)
    with db.transaction() as conn:
        assert conn.execute('PRAGMA user_version').fetchone()[0] == 11
        assert conn.execute("SELECT 1 FROM users WHERE id='preserved'").fetchone()
        assert conn.execute("SELECT COUNT(*) FROM sqlite_master WHERE name LIKE 'program_%'").fetchone()[0] == 0


def test_inactive_provider_redacts_outing_but_keeps_owner_unlink_action(programs):
    db = programs.app.state.database
    program_content(db, programs.settings, NOW)
    aoi, ren = programs.client('aoi'), programs.client('ren')
    with db.transaction(True) as conn:
        conn.execute("UPDATE providers SET active=0 WHERE id='ops26-provider-1'")
    item = find(aoi)
    assert not item['available']
    first = item['enrollment']['steps'][0]
    assert first['has_link'] and first['outing_id'] is None and first['status'] == 'invalid'
    assert PID not in [row['id'] for row in ren.get(BASE).json()['items']]
    removed = link(aoi, 'shape', None, item['enrollment']['version'])
    assert removed.status_code == 200, removed.text
    assert not removed.json()['steps'][0]['has_link']
    assert removed.json()['steps'][0]['outing_id'] is None
    cancelled = aoi.write('POST', BASE + '/' + PID + '/cancel',
                         dict(version=removed.json()['version'], client_request_id='inactive-cancel'))
    assert cancelled.status_code == 200 and cancelled.json()['status'] == 'cancelled'
    with db.transaction() as conn:
        assert conn.execute("SELECT COUNT(*) FROM daytrip_participants WHERE outing_id='program26-outing-past-0'").fetchone()[0] == 6
