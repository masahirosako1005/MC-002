"""Explicit fictional purpose-specific plans; never a startup migration."""
import argparse
import json
from datetime import UTC, datetime, timedelta

from ..config import Settings
from ..database import Database
from ..marketplace.schemas import ProviderPlanInput
from ..marketplace.service import Marketplace, dump
from ..operational_seed import PACK as OPERATING_PACK
from ..operational_seed import ContentPack, stamp
from .catalog import PROGRAMS, plan_id
from .service import Programs

PACK = 'program-content-20261110-v1'


def add_plans(conn, at):
    for program in PROGRAMS:
        staff = conn.execute('''SELECT s.user_id FROM provider_staff s JOIN providers p ON p.id=s.provider_id
            WHERE s.provider_id=? AND s.active=1 AND p.active=1 ORDER BY s.user_id LIMIT 1''', (program['provider_id'],)).fetchone()
        if staff is None:
            raise ValueError('Apply the operating content pack before the program plans')
        for sid, title, purpose, price in program['steps']:
            pid = plan_id(program['id'], sid)
            body = dict(title=title, summary=purpose, area='N西市', min_people=2, max_people=8,
                nights=0, price_yen=price, price_basis='per_person', price_scope='plan_only',
                price_note='この回の体験と材料の一人料金です。往復交通費・昼食は含みません。日程と予約は相談で確認します。',
                tags=program['tags'], itinerary=[dict(day=1, period='morning', place='N西市・体験会場', description=purpose, travel_minutes=20),
                    dict(day=1, period='afternoon', place='N西市・体験会場', description='工程を振り返り、次回の予定を相談します。', travel_minutes=20)],
                schedule_type='on_request', starts_at=None, ends_at=None)
            ProviderPlanInput.model_validate(body | {'status': 'published'})
            conn.execute("INSERT INTO provider_plans VALUES(?,?,?,'published',1,?)", (pid, program['provider_id'], dump(body), at.isoformat()))
            conn.execute('INSERT INTO daytrip_plan_routes VALUES(?,?,?,?)', (pid, program['route_id'], staff['user_id'], at.isoformat()))


class FirstStage(ContentPack):
    @staticmethod
    def key(kind, *parts):
        return 'program26-' + kind + '-' + '-'.join(str(part) for part in parts)

    def photo_journal(self, uid, number, day, room, end):
        # This fixture adds a verified stage, not a photograph of a finished work.
        return None


def add_first_stage(conn, database, settings, at):
    builder = FirstStage(conn, database, settings, at)
    members = ['u-aoi'] + [f'extra26-person-{index:03}' for index in range(5)]
    for uid in members:
        if not conn.execute("SELECT 1 FROM users u JOIN memberships m ON m.user_id=u.id WHERE u.id=? AND u.login_enabled=1 AND m.community_id='peers' AND m.status='active'", (uid,)).fetchone():
            raise ValueError('An existing participant is unavailable; no membership was restored')
    occupied = {row['day'] for row in conn.execute('SELECT user_id,day FROM daytrip_daily_awards') if row['user_id'] in members}
    day = next((builder.today - timedelta(days=offset) for offset in range(3, 30)
                if (builder.today - timedelta(days=offset)).isoformat() not in occupied), None)
    if day is None:
        raise ValueError('No unused daily award date is available for the first stage')
    definition = PROGRAMS[0]
    plan = conn.execute('SELECT * FROM provider_plans WHERE id=?', (plan_id(definition['id'], 'shape'),)).fetchone()
    staff = conn.execute('SELECT user_id FROM provider_staff WHERE provider_id=? AND active=1 ORDER BY user_id LIMIT 1', (definition['provider_id'],)).fetchone()[0]
    builder.providers = [(definition['provider_id'], staff)]
    builder.plans = {0: Marketplace(database).plan_out(conn, plan)}
    room = builder.room(0, 0, members, day)
    oid = builder.outing(0, members, room, day)
    snapshot = dump(Programs(database).public(conn, definition['id']))
    conn.execute("INSERT INTO program_enrollments VALUES('u-aoi',?,1,?,'active',?)", (definition['id'], stamp(day - timedelta(days=15)).isoformat(), snapshot))
    conn.execute("INSERT INTO program_step_links VALUES('u-aoi',?,'shape',?,?)", (definition['id'], oid, at.isoformat()))
    conn.execute("INSERT INTO program_events VALUES('program26-enrolled','u-aoi',?,'enrolled','{}',?)", (definition['id'], at.isoformat()))
    return oid


def apply(database, settings, at=None, *, history=True):
    at = at or datetime.now(UTC)
    with database.transaction(True) as conn:
        previous = conn.execute('SELECT value FROM settings WHERE key=?', (PACK,)).fetchone()
        if previous:
            return json.loads(previous['value']) | {'already_applied': True}
        if conn.execute('PRAGMA user_version').fetchone()[0] != 12:
            raise ValueError('Schema 12 is required')
        if not conn.execute('SELECT 1 FROM settings WHERE key=?', (OPERATING_PACK,)).fetchone():
            raise ValueError('Apply the operating content pack first')
        add_plans(conn, at - timedelta(days=100))
        outing = add_first_stage(conn, database, settings, at) if history else None
        result = dict(pack=PACK, already_applied=False, programs=2, plans=6,
            first_stage_outing=outing, provenance='Explicitly requested fictional purpose-specific activities; not real visits', applied_at=at.isoformat())
        if conn.execute('PRAGMA foreign_key_check').fetchone():
            raise ValueError('Program content has invalid references')
        conn.execute('INSERT INTO settings VALUES(?,?)', (PACK, dump(result)))
        return result


def main():
    parser = argparse.ArgumentParser(description='Append fictional purpose-specific programs once')
    parser.add_argument('--apply', action='store_true', required=True)
    parser.parse_args()
    settings = Settings()
    print(json.dumps(apply(Database(settings.db_path), settings), ensure_ascii=False))


if __name__ == '__main__':
    main()
