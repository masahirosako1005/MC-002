"""Explicit append-only fictional operating history; never run at startup."""
import argparse
import hashlib
import json
import secrets
from collections import Counter
from datetime import UTC, datetime, time, timedelta, timezone
from pathlib import Path

from .config import Settings
from .database import Database, password_hash
from .daytrip.catalog import ROUTES
from .enrichment import INSERT_SQL as BASE_SQL
from .enrichment import PACK as BASE_PACK
from .images import sanitize_image
from .marketplace.schemas import ProviderPlanInput
from .marketplace.service import Marketplace, dump

PACK = 'operational-content-20261110-v1'
PREFIX = 'ops26-'
JST = timezone(timedelta(hours=9))
INITIAL = ('u-aoi', 'u-ren', 'u-mio')
ROUTE_IDS = (
    'osaka-nnishi-market', 'osaka-nnishi-satoyama', 'osaka-nnishi-riverside',
    'osaka-nnishi-pottery', 'osaka-nnishi-teahouse', 'osaka-nnishi-oldroad', 'osaka-nnishi-garden',
)
TOPICS = (
    ('門前朝市と昼ごはん', ['food', 'walk'], 'coffee', '門前朝市'),
    ('北山の里道さんぽ', ['mountain', 'nature'], 'woodland', '北山の散策路'),
    ('川辺の食堂と散策', ['food', 'nature'], 'riverside', '川辺の遊歩道'),
    ('陶房で器をつくる', ['fashion', 'cafe'], 'pottery', '門前の陶房'),
    ('茶店と季節のお菓子', ['cafe', 'food'], 'coffee', '北山の茶店'),
    ('旧道の小さな店めぐり', ['walk', 'fashion'], 'woodland', '旧道の商店街'),
    ('庭園の散策と休憩', ['nature', 'cafe'], 'garden', '中央庭園'),
)
SQL = BASE_SQL | {
    'providers': 'INSERT INTO providers(id,name,description,area,active) VALUES(?,?,?,?,?)',
    'provider_staff': 'INSERT INTO provider_staff(provider_id,user_id,active) VALUES(?,?,?)',
    'circle_member_invitations': 'INSERT INTO circle_member_invitations(id,party_id,invitee_id,inviter_id,status,version,created_at) VALUES(?,?,?,?,?,?,?)',
    'circle_proposals': 'INSERT INTO circle_proposals(id,invitation_id,version,body,created_by,created_at) VALUES(?,?,?,?,?,?)',
    'circle_confirmations': 'INSERT INTO circle_confirmations(proposal_id,role,user_id,confirmed_at) VALUES(?,?,?,?)',
    'daytrip_events': 'INSERT INTO daytrip_events(id,outing_id,actor_id,kind,body,created_at) VALUES(?,?,?,?,?,?)',
    'journal_journeys': 'INSERT INTO journal_journeys(id,user_id,title,version,created_at) VALUES(?,?,?,?,?)',
    'journal_visits': 'INSERT INTO journal_visits(id,user_id,journey_id,prefecture_id,visited_on,place_label,latitude,longitude,media_id,source,visibility,community_id,version,created_at,updated_at) VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)',
}


def key(kind, *parts):
    return PREFIX + kind + '-' + '-'.join(str(part) for part in parts)


def stamp(day, hour=10, minute=0):
    return datetime.combine(day, time(hour, minute), JST).astimezone(UTC)


def preflight(conn):
    if conn.execute('PRAGMA user_version').fetchone()[0] not in (11, 12):
        raise ValueError('Schema 11 or 12 is required before this explicit content pack')
    if not conn.execute('SELECT 1 FROM settings WHERE key=?', (BASE_PACK,)).fetchone():
        raise ValueError('Apply the earlier fictional content pack first')
    users = [f'extra26-person-{index:03}' for index in range(36)] + list(INITIAL)
    for uid in users:
        if not conn.execute("SELECT 1 FROM users u JOIN memberships m ON m.user_id=u.id WHERE u.id=? AND u.login_enabled=1 AND m.community_id='peers' AND m.status='active'", (uid,)).fetchone():
            raise ValueError('A required fictional account is unavailable; existing membership will not be changed')
    if conn.execute('SELECT 1 FROM users WHERE id LIKE ?', (PREFIX + '%',)).fetchone():
        raise ValueError('Operational namespace exists without its manifest')
    if not set(ROUTE_IDS) <= {route['id'] for route in ROUTES}:
        raise ValueError('The expanded Nishi city route catalogue is required')


class ContentPack:
    key = staticmethod(key)

    def __init__(self, conn, database, settings, at):
        self.conn, self.db, self.settings, self.at = conn, database, settings, at
        self.today = at.astimezone(JST).date()
        self.counts = Counter()
        self.market = Marketplace(database)
        self.routes = {route['id']: route for route in ROUTES}
        directory = settings.seed_asset_dir or Path(__file__).resolve().parents[2] / 'assets'
        self.assets = {name: sanitize_image((directory / (name + '.png')).read_bytes(), settings)
                       for name in {topic[2] for topic in TOPICS}}
        self.providers = [('forest-house', 'provider-forest'), ('shore-school', 'provider-shore')]
        self.plans, self.rooms = {}, {}

    def put(self, table, **values):
        query = SQL[table]
        columns = query.split('(', 1)[1].split(')', 1)[0].split(',')
        if set(columns) != values.keys():
            raise ValueError('Unexpected operational content columns')
        self.conn.execute(query, tuple(values[column] for column in columns))
        self.counts[table] += 1

    def people(self):
        friends = []
        for index, name in enumerate(('中島 澪', '岡本 岳', '藤原 栞')):
            uid, salt = key('friend', index), secrets.token_hex(16)
            self.put('users', id=uid, username=uid, name=name, initials=name.split()[-1], color='#6F7257',
                salt=salt, password_hash=password_hash(secrets.token_urlsafe(32), salt), login_enabled=1)
            self.put('preferences', user_id=uid, tags=dump(['walk', 'cafe', 'nature']), learn_from_posts=0)
            self.put('memberships', community_id='peers', user_id=uid, role='member', status='active')
            self.put('grants', user_id=uid, community_id='peers', use_matching=1, display_matching=1, participate=1)
            friends.append(uid)
        # Existing residence and consent are never inferred or changed. The
        # three new companions also have no residence profile by default.
        return [[f'extra26-person-{group * 6 + member:03}' for member in range(6)] for group in range(6)] + [list(INITIAL) + friends]

    def businesses(self):
        for index, name in enumerate(('門前市場の案内所', 'N西くらしの陶房', '川辺と庭園の案内所', '北山の茶店')):
            pid = key('provider', index)
            staff = 'provider-forest' if index < 2 else 'provider-shore'
            self.put('providers', id=pid, name=name, description='人数と日程に合わせて日帰りの行程を相談できます。', area='N西市', active=1)
            self.put('provider_staff', provider_id=pid, user_id=staff, active=1)
            self.put('settings', key='city-provider:n-nishi:' + pid, value='1')
            self.providers.append((pid, staff))
        for pid, staff in self.providers:
            self.market.staff(self.conn, staff, pid)

    def make_plans(self):
        created = stamp(self.today - timedelta(days=100)).isoformat()
        for index in range(12):
            topic, tags, _, place = TOPICS[index % 7]
            pid, staff = self.providers[index // 2]
            plan_id, route = key('plan', index), self.routes[ROUTE_IDS[index % 7]]
            body = dict(title=topic + ('・少人数の休日' if index < 6 else '・午後の体験'),
                summary='午前の集合から夕方の帰着まで、休憩を挟んでめぐります。', area='N西市',
                min_people=2, max_people=8, nights=0, price_yen=4800 + index * 300,
                price_basis='per_person', price_scope='plan_only',
                price_note='体験と昼食の料金。大阪駅からの往復交通費は含みません。受入日は相談で確認します。',
                tags=tags, itinerary=[
                    dict(day=1, period='morning', place=place, description='集合してゆっくり散策します。', travel_minutes=20),
                    dict(day=1, period='afternoon', place='門前の食堂', description='昼食の後に体験を楽しみます。', travel_minutes=15),
                    dict(day=1, period='evening', place='N西市・中央広場', description='帰りの時刻を確認して解散します。', travel_minutes=20)],
                schedule_type='on_request', starts_at=None, ends_at=None)
            ProviderPlanInput.model_validate(body | {'status': 'published'})
            self.put('provider_plans', id=plan_id, provider_id=pid, body=dump(body), status='published', version=1, updated_at=created)
            self.put('daytrip_plan_routes', plan_id=plan_id, route_id=route['id'], updated_by=staff, updated_at=created)
            row = self.conn.execute('SELECT * FROM provider_plans WHERE id=?', (plan_id,)).fetchone()
            self.plans[index] = self.market.plan_out(self.conn, row)
            self.put('daytrip_benefits', id=key('benefit', index), provider_id=pid, plan_id=plan_id,
                title=topic + 'の利用特典', min_rank=2 if index % 2 == 0 else 4, discount_type='amount',
                discount_value=500 if index % 2 == 0 else 800, max_discount_yen=800, max_redemptions=200,
                starts_on=(self.today - timedelta(days=7)).isoformat(), ends_on=(self.today + timedelta(days=120)).isoformat(),
                status='published', created_at=stamp(self.today - timedelta(days=7)).isoformat())
            self.put('settings', key='daytrip-benefit-rank:' + key('benefit', index), value='R2')

    def schedule(self, cohorts):
        users = {uid for group in cohorts for uid in group}
        occupied = {row['day'] for row in self.conn.execute('SELECT user_id,day FROM daytrip_daily_awards WHERE day>=?',
            ((self.today - timedelta(days=70)).isoformat(),)) if row['user_id'] in users}
        dates = []
        for week in range(10, 0, -1):
            candidates = [self.today - timedelta(days=week * 7) + timedelta(days=offset) for offset in range(7)]
            available = [day for day in candidates if day < self.today - timedelta(days=1) and day.isoformat() not in occupied]
            if len(available) < 2:
                raise ValueError('Existing daily awards leave too few free days; nothing was overwritten')
            chosen = (available[0], available[-1])
            dates.extend(chosen)
            occupied.update(day.isoformat() for day in chosen)
        return dates

    def room(self, group, provider_index, members, first_day, future=False):
        suffix = ('future' if future else 'history', group, provider_index)
        cid, iid, sid, consultation = (self.key(kind, *suffix) for kind in ('circle', 'invite', 'selection', 'consult'))
        representative, plan = members[0], self.plans[provider_index * 2 + group % 2]
        pid, staff = self.providers[provider_index]
        created = stamp(self.today - timedelta(days=3)) if future else stamp(first_day - timedelta(days=14))
        invited, accepted = created + timedelta(days=1), created + timedelta(days=1, hours=2)
        title = plan['title'] + ('・次の休日' if future else '・季節の講')
        self.put('travel_parties', id=cid, community_id='peers', ko_group_id=None,
            representative_id=representative, title=title, status='open', created_at=created.isoformat())
        self.put('circle_rooms', party_id=cid, mode='manual', desired_count=6, tags=dump(plan['tags']), created_at=created.isoformat())
        for position, uid in enumerate(members):
            self.put('travel_party_members', party_id=cid, user_id=uid)
            if position:
                self.put('circle_member_invitations', id=self.key('member', *suffix, position), party_id=cid,
                    invitee_id=uid, inviter_id=representative, status='accepted', version=2, created_at=created.isoformat())
        for index, text in enumerate(('6人で集まって、次の日帰りを相談しましょう。',
            '午前は散策、昼は食堂で休憩したいです。', '夕方には帰れる日程なら参加できます。',
            f'{first_day.isoformat()}に、{plan["title"]}で相談しましょう。人数と料金範囲を確認しました。')):
            self.put('party_messages', id=self.key('private', *suffix, index), party_id=cid,
                author_id=members[index % 6], body=text, created_at=(created + timedelta(hours=index + 1)).isoformat())
        conditions = dict(planned_people=6, nights=0, budget_yen=plan['price_yen'] + 2000,
            budget_basis='per_person', budget_scope='plan_only', date_start=first_day.isoformat())
        self.put('travel_requirements', party_id=cid, body=dump(conditions | dict(interests=plan['tags'], departure_label='大阪駅')),
            version=1, confirmed_by=representative, confirmed_at=(created + timedelta(hours=5)).isoformat())
        snapshot = dict(plan=plan, shared_conditions=conditions, share_note='6人で午前10時から、休憩を入れて夕方に帰る行程を相談します。',
            requirements_version=1, unknowns=['予約は別途確認'])
        self.put('plan_selections', id=sid, party_id=cid, plan_id=plan['id'], provider_id=pid,
            snapshot=dump(snapshot), selected_by=representative, status='active', created_at=accepted.isoformat())
        self.put('consultations', id=consultation, selection_id=sid, status='open', created_at=accepted.isoformat())
        self.put('circle_provider_invitations', id=iid, party_id=cid, provider_id=pid, inviter_id=representative,
            snapshot=dump(snapshot), status='accepted', consultation_id=consultation,
            created_at=invited.isoformat(), accepted_at=accepted.isoformat())
        messages = ((representative, '参加の承諾ありがとうございます。午前10時集合でお願いします。'),
                    (staff, '承知しました。6人で昼食前に一度休憩できる行程にします。'),
                    (members[1], '食事の時間と、帰りの集合場所も確認したいです。'),
                    (staff, '昼食は12時、帰りは中央広場に16時集合です。予約はこの会話だけでは確定しません。'))
        for index, (uid, text) in enumerate(messages):
            self.put('consultation_messages', id=self.key('shared', *suffix, index), consultation_id=consultation,
                author_id=uid, body=text, created_at=(accepted + timedelta(minutes=15 * (index + 1))).isoformat())
        proposal = self.key('proposal', *suffix)
        agreement = dict(title=plan['title'] + 'の行程', date_start=first_day.isoformat(), itinerary=plan['itinerary'],
            estimated_price_yen=plan['price_yen'], price_basis='per_person', price_scope='plan_only',
            price_note=plan['price_note'], unknowns=['営業・空席と予約確定は別途確認'])
        self.put('circle_proposals', id=proposal, invitation_id=iid, version=1, body=dump(agreement),
            created_by=staff, created_at=(accepted + timedelta(hours=2)).isoformat())
        for role, uid in (('traveler', representative), ('provider', staff)):
            self.put('circle_confirmations', proposal_id=proposal, role=role, user_id=uid,
                confirmed_at=(accepted + timedelta(hours=3)).isoformat())
        return dict(id=cid, invitation=iid, consultation=consultation, plan=plan, staff=staff, provider=pid)

    def event(self, oid, uid, kind, body, at, suffix):
        self.put('daytrip_events', id=self.key('event', oid, suffix), outing_id=oid, actor_id=uid,
            kind=kind, body=dump(body), created_at=at.isoformat())

    def outing(self, number, members, room, day, future=False):
        oid = self.key('outing', 'future' if future else 'past', number)
        plan = room['plan']
        route_id = self.conn.execute('SELECT route_id FROM daytrip_plan_routes WHERE plan_id=?', (plan['id'],)).fetchone()[0]
        route = self.routes[route_id] | {'zone': 'target'}
        start, end = stamp(day, 9), stamp(day, 18)
        created = stamp(self.today - timedelta(days=1), 8) if future else start - timedelta(days=3)
        leader = members[number % 6]
        self.put('daytrip_outings', id=oid, circle_id=room['id'], title=plan['title'], route_json=dump(route),
            starts_at=start.isoformat(), ends_at=end.isoformat(), day=day.isoformat(), status='scheduled' if future else 'confirmed',
            leader_id=leader, leader_accepted=1, plan_id=plan['id'], provider_id=room['provider'], invitation_id=room['invitation'],
            plan_json=dump(plan | dict(provider_id=room['provider'])), created_by=members[0], created_at=created.isoformat())
        self.event(oid, members[0], 'created', {'leader_id': leader}, created, 'create')
        accepted = created + timedelta(hours=2)
        for index, uid in enumerate(members):
            points = 0 if future else 100 + int(min(route['one_way_km'] * 2, 200) // 10) + (50 if uid == leader else 0)
            witness = members[(index + 1) % 6]
            self.put('daytrip_participants', outing_id=oid, user_id=uid, accepted=1, claimed=int(not future),
                full_route=int(not future), confirmed_by=None if future else witness, provider_verified=int(not future), points=points, revoked=0)
            self.event(oid, uid, 'accepted', {'leader': uid == leader}, accepted, 'accept-' + str(index))
            if not future:
                self.completed_person(oid, uid, witness, points, end, index)
                if uid in INITIAL:
                    self.photo_journal(uid, number, day, room, end)
        if not future:
            self.event(oid, room['staff'], 'provider_verified', {'participants': members}, end + timedelta(hours=1), 'verify')
        self.put('party_messages', id=self.key('outing-private', number, int(future)), party_id=room['id'], author_id=members[0],
            body=f'{day.isoformat()}は大阪駅で9時集合です。持ち物と帰りの時刻を確認しましょう。',
            created_at=(created + timedelta(hours=1)).isoformat())
        self.put('consultation_messages', id=self.key('outing-shared', number, int(future)), consultation_id=room['consultation'],
            author_id=room['staff'], body=f'{day.isoformat()}の6人分の行程を確認しました。帰りの集合は中央広場です。',
            created_at=(created + timedelta(hours=2)).isoformat())
        return oid

    def completed_person(self, oid, uid, witness, points, end, index):
        day = end.astimezone(JST).date().isoformat()
        self.put('daytrip_daily_awards', user_id=uid, day=day, outing_id=oid)
        for kind, credit, eligible, minute in (('award', points, 0, 30), ('verify', 0, points, 60)):
            self.put('daytrip_ledger', id=self.key(kind, oid, index), outing_id=oid, user_id=uid, kind=kind,
                points=credit, eligible_points=eligible, reason='参加者と事業者が利用を確認', rule_version='D1',
                created_at=(end + timedelta(minutes=minute)).isoformat())
        self.event(oid, uid, 'claimed', {'full_route': True}, end + timedelta(minutes=15), 'claim-' + str(index))
        self.event(oid, witness, 'participant_confirmed', {'participant_id': uid, 'points': points},
            end + timedelta(minutes=30), 'confirm-' + str(index))

    def photo_journal(self, uid, number, day, room, end):
        plan_index = next(index for index, plan in self.plans.items() if plan['id'] == room['plan']['id'])
        topic, tags, cover, place = TOPICS[plan_index % 7]
        mid, pid = self.key('media', uid, number), self.key('post', uid, number)
        clean, width, height = self.assets[cover]
        path = self.settings.media_dir / (mid + '.jpg')
        if path.exists() and path.read_bytes() != clean:
            raise ValueError('Operational media collision; existing bytes are untouched')
        if not path.exists():
            path.write_bytes(clean)
        at = (end + timedelta(hours=2)).isoformat()
        self.put('media', id=mid, user_id=uid, storage_key=path.name, width=width, height=height,
            sha256=hashlib.sha256(clean).hexdigest(), created_at=at)
        self.put('jobs', media_id=mid, status='manual', tags='[]', message='投稿者がタグを選びました。')
        self.put('posts', id=pid, user_id=uid, community_id='peers', body=f'{topic}に6人で出かけました。途中で休憩を取り、夕方に帰りました。次は違う季節にも歩きたいです。',
            tags=dump(tags), status='published', place_label='N西市・' + place, taken_on=day.isoformat(), created_at=at)
        self.put('post_media', post_id=pid, media_id=mid, position=0)
        journey = self.key('journey', uid, number // 14)
        if not self.conn.execute('SELECT 1 FROM journal_journeys WHERE id=?', (journey,)).fetchone():
            self.put('journal_journeys', id=journey, user_id=uid, title=f'{day.month}月{day.day}日の週・N西市', version=1, created_at=at)
        self.put('journal_visits', id=self.key('visit', uid, number), user_id=uid, journey_id=journey,
            prefecture_id='27', visited_on=day.isoformat(), place_label='N西市・' + place,
            latitude=round(34.83 + (plan_index % 7) * 0.001, 3), longitude=round(135.50 + (plan_index % 7) * 0.002, 3),
            media_id=mid, source='manual', visibility='private', community_id=None, version=1, created_at=at, updated_at=at)

    def run(self):
        cohorts = self.people()
        self.businesses()
        self.make_plans()
        dates = self.schedule(cohorts)
        for index, day in enumerate(dates):
            provider_index = index % 6
            for group, members in enumerate(cohorts):
                identity = (group, provider_index)
                if identity not in self.rooms:
                    self.rooms[identity] = self.room(group, provider_index, members, day)
                self.outing(index * 7 + group, members, self.rooms[identity], day)
        upcoming = []
        for provider_index in range(6):
            day = self.today + timedelta(days=3 + provider_index * 3)
            room = self.room(6, provider_index, cohorts[6], day, future=True)
            upcoming.append(self.outing(provider_index, cohorts[6], room, day, future=True))
        return dict(pack=PACK, applied_at=self.at.isoformat(), already_applied=False,
            counts=dict(self.counts), weeks=10, cohort_size=6, cohorts=7,
            first_day=dates[0].isoformat(), last_day=dates[-1].isoformat(), completed_outings=140,
            future_outings=len(upcoming), initial_account_visits_each=20,
            provenance='Explicitly requested fictional local operating history; not survey data or measured tourism outcomes',
            prior_rows_updated=0, existing_residence_or_consent_changed=False, original_photos_changed=False)


def apply(database, settings, at=None):
    instant = at or datetime.now(UTC)
    settings.media_dir.mkdir(parents=True, exist_ok=True)
    with database.transaction(True) as conn:
        saved = conn.execute('SELECT value FROM settings WHERE key=?', (PACK,)).fetchone()
        if saved:
            return json.loads(saved['value']) | {'already_applied': True}
        preflight(conn)
        result = ContentPack(conn, database, settings, instant).run()
        if conn.execute('PRAGMA foreign_key_check').fetchone():
            raise ValueError('Operational content has invalid references')
        conn.execute('INSERT INTO settings VALUES(?,?)', (PACK, dump(result)))
        return result


def main():
    parser = argparse.ArgumentParser(description='Append requested fictional operating history once')
    parser.add_argument('--apply', action='store_true', required=True)
    parser.parse_args()
    settings = Settings()
    print(json.dumps(apply(Database(settings.db_path), settings), ensure_ascii=False))


if __name__ == '__main__':
    main()
