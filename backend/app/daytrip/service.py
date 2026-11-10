"""Authoritative local records. Claims never establish monetary eligibility."""
import json
from datetime import UTC, datetime, timedelta, timezone
from decimal import Decimal

from fastapi import HTTPException

from ..database import identifier, now
from ..marketplace.service import Marketplace, conflict, dump
from ..service import require
from .catalog import ROUTES
from .ranks import (
    FLOOR_MAX,
    LEGACY_LEVELS,
    NAMES,
    THRESHOLDS,
    VERSION,
    WINDOW_DAYS,
    benefit_level,
    benefit_policy,
    capture_evidence,
    evaluate,
    evidence_status,
    legacy_eligible_points,
)
from .ranks import rank as rank
from .zone_benefits import (
    budget_status,
    can_configure,
    configure,
    personal_offer,
    reservation_discount,
    used_yen,
)

JST = timezone(timedelta(hours=9))
RULES = dict(version='D1', base_points=100, distance_cap_km=200, leader_points=50,
             rank_thresholds=list(THRESHOLDS), rank_names=list(NAMES), rank_policy_version=VERSION,
             rank_window_days=WINDOW_DAYS, rank_lifetime_floor_max=FLOOR_MAX)


def clock_now():
    return datetime.now(UTC)


def route_out(route):
    result = dict(route)
    km, minutes = route.get('one_way_km'), route.get('one_way_minutes')
    if km is None or minutes is None:
        zone = 'unknown'
    elif 20 <= km <= 40:
        zone = 'target'
    elif km < 20:
        zone = 'nearby'
    else:
        zone = 'outside'
    return result | {'zone': zone}


class Daytrip:
    def __init__(self, database):
        self.db = database
        self.market = Marketplace(database)

    @staticmethod
    def route(route_id):
        return route_out(require(next((item for item in ROUTES if item['id'] == route_id), None)))

    @staticmethod
    def version(row, version):
        if row['version'] != version:
            conflict()

    @staticmethod
    def event(conn, outing_id, uid, kind, body):
        conn.execute('INSERT INTO daytrip_events VALUES(?,?,?,?,?,?)', (identifier(), outing_id, uid, kind, dump(body), now()))

    @staticmethod
    def person(conn, oid, uid):
        return require(conn.execute('SELECT * FROM daytrip_participants WHERE outing_id=? AND user_id=?', (oid, uid)).fetchone())

    def active_person(self, conn, row, uid):
        party = self.market.party(conn, uid, row['circle_id'])
        if party['status'] != 'open':
            raise HTTPException(409, 'この講の計画は閉じています。')
        person = self.person(conn, row['id'], uid)
        if person['revoked']:
            raise HTTPException(409, 'この参加記録は取り消されています。')
        return person

    def access(self, conn, uid, oid, provider=False, manage=False):
        row = require(conn.execute('SELECT * FROM daytrip_outings WHERE id=?', (oid,)).fetchone())
        if provider:
            self.market.staff(conn, uid, row['provider_id'])
            require(conn.execute("SELECT 1 FROM circle_provider_invitations i JOIN travel_parties p ON p.id=i.party_id WHERE i.id=? AND i.status='accepted' AND p.status='open'", (row['invitation_id'],)).fetchone())
        else:
            party = self.market.party(conn, uid, row['circle_id'])
            if manage and party['representative_id'] != uid:
                raise HTTPException(404, '開催が見つかりません。')
        return row

    @staticmethod
    def mutable(row):
        if row['status'] == 'cancelled':
            raise HTTPException(409, '中止した開催です。')

    @staticmethod
    def before_start(row):
        if clock_now() >= datetime.fromisoformat(row['starts_at']):
            raise HTTPException(409, '出発前に設定・参加承諾を済ませてください。')

    @staticmethod
    def after_end(row):
        if clock_now() < datetime.fromisoformat(row['ends_at']):
            raise HTTPException(409, '開催が終了してから実参加を確認してください。')

    def out(self, conn, uid, row, provider=False):
        party = conn.execute('SELECT representative_id FROM travel_parties WHERE id=?', (row['circle_id'],)).fetchone()
        people = [dict(item) for item in conn.execute('SELECT p.user_id,u.name,p.accepted,p.claimed,p.full_route,p.confirmed_by,p.provider_verified,p.points,p.revoked FROM daytrip_participants p JOIN users u ON u.id=p.user_id WHERE p.outing_id=? ORDER BY u.id', (row['id'],))]
        for person in people:
            for key in ('accepted','claimed','full_route','provider_verified','revoked'):
                person[key] = bool(person[key])
        result = {key: row[key] for key in ('id','circle_id','title','starts_at','ends_at','status','version','leader_id','leader_accepted','plan_id','provider_id','created_at')}
        result['leader_accepted'] = bool(result['leader_accepted'])
        return result | dict(route=json.loads(row['route_json']), participants=people, can_manage=not provider and party['representative_id'] == uid, is_provider=provider)

    def current_out(self, conn, uid, oid, provider=False):
        return self.out(conn, uid, conn.execute('SELECT * FROM daytrip_outings WHERE id=?', (oid,)).fetchone(), provider)

    def catalog(self):
        with self.db.transaction() as conn:
            links = [dict(row) for row in conn.execute("SELECT l.plan_id,p.provider_id,l.route_id,json_extract(p.body,'$.title') AS plan_title,v.name AS provider_name,v.area FROM daytrip_plan_routes l JOIN provider_plans p ON p.id=l.plan_id JOIN providers v ON v.id=p.provider_id WHERE p.status='published' AND v.active=1 ORDER BY l.route_id,l.plan_id")]
            return dict(routes=[route_out(item) for item in ROUTES], rules=RULES, plans=links)

    def outings(self, uid, cid):
        with self.db.transaction() as conn:
            self.market.party(conn, uid, cid)
            return {'items': [self.out(conn, uid, row) for row in conn.execute('SELECT * FROM daytrip_outings WHERE circle_id=? ORDER BY starts_at DESC,id LIMIT 100', (cid,))]}

    def get(self, uid, oid):
        with self.db.transaction() as conn:
            provider = conn.execute('SELECT 1 FROM daytrip_outings o JOIN provider_staff s ON s.provider_id=o.provider_id JOIN providers p ON p.id=s.provider_id WHERE o.id=? AND s.user_id=? AND s.active=1 AND p.active=1', (oid,uid)).fetchone() is not None
            return self.out(conn, uid, self.access(conn, uid, oid, provider=provider), provider)

    def public_plan(self, conn, plan_id):
        row = require(conn.execute("SELECT p.* FROM provider_plans p JOIN providers v ON v.id=p.provider_id WHERE p.id=? AND p.status='published' AND v.active=1", (plan_id,)).fetchone())
        plan = json.loads(row['body'])
        if plan['nights'] != 0:
            raise HTTPException(409, '0泊の日帰りプランを選んでください。')
        return row, plan

    def create(self, uid, cid, data):
        with self.db.transaction(True) as conn:
            self.market.party(conn, uid, cid, True)
            previous, fingerprint = self.market.replay(conn, uid, 'daytrip:create:' + cid, data)
            if previous:
                return self.current_out(conn, uid, previous)
            route = self.route(data['route_id'])
            start, end = (datetime.fromisoformat(data[key]) for key in ('starts_at', 'ends_at'))
            if start <= clock_now() or end <= start or start.astimezone(JST).date() != end.astimezone(JST).date():
                raise HTTPException(422, 'これから出発して同じ日に帰る日時を選んでください。')
            if route.get('one_way_minutes') is not None and (end - start).total_seconds() < route['one_way_minutes'] * 120:
                raise HTTPException(422, '往復の参考移動時間を確保できる日時を選んでください。')
            if uid not in data['participant_ids']:
                raise HTTPException(422, '代表者を参加者に含めてください。')
            for person in data['participant_ids']:
                self.market.party(conn, person, cid)
                require(conn.execute('SELECT 1 FROM users WHERE id=? AND login_enabled=1', (person,)).fetchone())
            plan_id, provider_id, invitation_id, plan_snapshot = data.get('plan_id'), None, None, None
            if plan_id:
                plan_row, plan = self.public_plan(conn, plan_id)
                if not plan['min_people'] <= len(data['participant_ids']) <= plan['max_people']:
                    raise HTTPException(422, 'プランの対象人数に合わせてください。')
                if plan.get('schedule_type') == 'dated' and datetime.fromisoformat(plan['starts_at']).astimezone(JST).date() != start.astimezone(JST).date():
                    raise HTTPException(422, 'プランの開催日と合わせてください。')
                if plan.get('schedule_type') == 'dated' and (start > datetime.fromisoformat(plan['starts_at']) or end < datetime.fromisoformat(plan['ends_at'])):
                    raise HTTPException(422, 'プランの開始から終了まで参加できる開催日時を指定してください。')
                provider_id = plan_row['provider_id']
                require(conn.execute('SELECT 1 FROM daytrip_plan_routes WHERE plan_id=? AND route_id=?', (plan_id, route['id'])).fetchone())
                invitation = require(conn.execute("SELECT * FROM circle_provider_invitations WHERE party_id=? AND provider_id=? AND status='accepted'", (cid, provider_id)).fetchone())
                shared_plan = json.loads(invitation['snapshot'])['plan']
                if shared_plan['id'] != plan_id:
                    raise HTTPException(409, 'このプランの事業者参加を先に確認してください。')
                if shared_plan.get('version') != plan_row['version']:
                    raise HTTPException(409, '事業者プランが更新されています。講で最新版を選び直し、事業者への共有と参加承諾を確認してください。')
                invitation_id = invitation['id']
                plan_snapshot = dump(dict(plan, id=plan_id, version=plan_row['version'], provider_id=provider_id))
            if conn.execute('SELECT COUNT(*) FROM daytrip_outings WHERE circle_id=?', (cid,)).fetchone()[0] >= 200:
                raise HTTPException(409, 'この講の開催は200件までです。')
            oid = identifier()
            conn.execute("INSERT INTO daytrip_outings(id,circle_id,title,route_json,starts_at,ends_at,day,status,leader_id,plan_id,provider_id,invitation_id,plan_json,created_by,created_at) VALUES(?,?,?,?,?,?,?,'scheduled',?,?,?,?,?,?,?)", (oid,cid,data['title'],dump(route),start.astimezone(UTC).isoformat(),end.astimezone(UTC).isoformat(),start.astimezone(JST).date().isoformat(),data['leader_id'],plan_id,provider_id,invitation_id,plan_snapshot,uid,now()))
            conn.executemany('INSERT INTO daytrip_participants(outing_id,user_id) VALUES(?,?)', [(oid, person) for person in data['participant_ids']])
            self.event(conn, oid, uid, 'created', {'leader_id': data['leader_id']})
            self.market.remember(conn, uid, 'daytrip:create:' + cid, data, fingerprint, oid)
            return self.current_out(conn, uid, oid)

    def leader(self, uid, oid, data):
        with self.db.transaction(True) as conn:
            row = self.access(conn, uid, oid, manage=True)
            self.mutable(row)
            self.version(row, data['version'])
            self.before_start(row)
            self.active_person(conn, row, data['leader_id'])
            conn.execute('UPDATE daytrip_outings SET leader_id=?,leader_accepted=0,version=version+1 WHERE id=?', (data['leader_id'], oid))
            self.event(conn, oid, uid, 'leader_changed', {'from': row['leader_id'], 'to': data['leader_id']})
            return self.current_out(conn, uid, oid)

    def accept(self, uid, oid, data):
        with self.db.transaction(True) as conn:
            row = self.access(conn, uid, oid)
            self.mutable(row)
            self.version(row, data['version'])
            self.before_start(row)
            self.active_person(conn, row, uid)
            if data['accept_leader'] and uid != row['leader_id']:
                raise HTTPException(409, '先達に指名された本人が承諾してください。')
            conn.execute('UPDATE daytrip_participants SET accepted=1 WHERE outing_id=? AND user_id=?', (oid, uid))
            conn.execute('UPDATE daytrip_outings SET leader_accepted=CASE WHEN ? THEN 1 ELSE leader_accepted END,version=version+1 WHERE id=?', (data['accept_leader'], oid))
            self.event(conn, oid, uid, 'accepted', {'leader': data['accept_leader']})
            return self.current_out(conn, uid, oid)

    def claim(self, uid, oid, data):
        with self.db.transaction(True) as conn:
            row = self.access(conn, uid, oid)
            self.mutable(row)
            self.version(row, data['version'])
            self.after_end(row)
            person = self.active_person(conn, row, uid)
            if not person['accepted'] or not row['leader_accepted']:
                raise HTTPException(409, '出発前の参加・先達承諾が必要です。')
            if person['confirmed_by']:
                raise HTTPException(409, '確認済みの参加記録です。訂正は取消として記録してください。')
            if conn.execute('SELECT COUNT(*) FROM daytrip_participants WHERE outing_id=? AND accepted=1 AND revoked=0', (oid,)).fetchone()[0] < 2:
                raise HTTPException(409, '2人以上の参加承諾が必要です。')
            conn.execute('UPDATE daytrip_participants SET claimed=1,full_route=? WHERE outing_id=? AND user_id=?', (data['full_route'], oid, uid))
            conn.execute("UPDATE daytrip_outings SET status='reporting',version=version+1 WHERE id=?", (oid,))
            self.event(conn, oid, uid, 'claimed', {'full_route': data['full_route']})
            return self.current_out(conn, uid, oid)

    def confirm(self, uid, oid, data):
        with self.db.transaction(True) as conn:
            row = self.access(conn, uid, oid)
            self.mutable(row)
            self.version(row, data['version'])
            self.after_end(row)
            actor = self.active_person(conn, row, uid)
            target = self.active_person(conn, row, data['participant_id'])
            if uid == target['user_id'] or not actor['claimed'] or not target['claimed']:
                raise HTTPException(409, '参加を申告した別の仲間が確認してください。')
            if target['confirmed_by']:
                return self.current_out(conn, uid, oid)
            previous = conn.execute('SELECT outing_id FROM daytrip_daily_awards WHERE user_id=? AND day=?', (target['user_id'], row['day'])).fetchone()
            if previous and previous['outing_id'] != oid:
                raise HTTPException(409, '同じ日のポイント付与は一人一開催までです。取消後も同日の再付与はできません。')
            route = json.loads(row['route_json'])
            km = route.get('one_way_km')
            distance = int(min(Decimal(str(km)) * 2, Decimal(200)) // 10) if km is not None and target['full_route'] else 0
            leader = 50 if target['user_id'] == row['leader_id'] and row['leader_accepted'] and target['full_route'] else 0
            points = 100 + distance + leader
            if not previous:
                conn.execute('INSERT INTO daytrip_daily_awards VALUES(?,?,?)', (target['user_id'], row['day'], oid))
            conn.execute('UPDATE daytrip_participants SET confirmed_by=?,points=? WHERE outing_id=? AND user_id=?', (uid, points, oid, target['user_id']))
            reason = f'参加100点・参考往復距離{distance}点・先達{leader}点'
            conn.execute('INSERT INTO daytrip_ledger VALUES(?,?,?,?,?,?,?,?,?)', (identifier(),oid,target['user_id'],'award',points,0,reason,'D1',now()))
            remaining = conn.execute('SELECT COUNT(*) FROM daytrip_participants WHERE outing_id=? AND confirmed_by IS NULL AND revoked=0', (oid,)).fetchone()[0]
            conn.execute('UPDATE daytrip_outings SET status=?,version=version+1 WHERE id=?', ('confirmed' if remaining == 0 else 'reporting', oid))
            self.event(conn, oid, uid, 'participant_confirmed', {'participant_id': target['user_id'], 'points': points})
            return self.current_out(conn, uid, oid)

    def provider_confirm(self, uid, oid, data):
        with self.db.transaction(True) as conn:
            row = self.access(conn, uid, oid, provider=True)
            self.mutable(row)
            self.version(row, data['version'])
            self.after_end(row)
            for target_id in data['participant_ids']:
                person = self.active_person(conn, row, target_id)
                if not person['confirmed_by'] or person['points'] <= 0:
                    raise HTTPException(409, '仲間の実参加確認が先に必要です。')
                if conn.execute('SELECT 1 FROM provider_staff WHERE provider_id=? AND user_id=?', (row['provider_id'], target_id)).fetchone():
                    raise HTTPException(409, '自社スタッフの参加は特典資格の対象にできません。')
                if not person['provider_verified']:
                    conn.execute('UPDATE daytrip_participants SET provider_verified=1 WHERE outing_id=? AND user_id=?', (oid, target_id))
                    conn.execute('INSERT INTO daytrip_ledger VALUES(?,?,?,?,?,?,?,?,?)', (identifier(),oid,target_id,'verify',0,person['points'],'事業者の利用確認により特典対象へ','D1',now()))
            conn.execute('UPDATE daytrip_outings SET version=version+1 WHERE id=?', (oid,))
            self.event(conn, oid, uid, 'provider_verified', {'participants': data['participant_ids']})
            return self.current_out(conn, uid, oid, True)

    def reverse_person(self, conn, oid, target_id, reason, revoke=True):
        balance = conn.execute('SELECT COALESCE(SUM(points),0),COALESCE(SUM(eligible_points),0) FROM daytrip_ledger WHERE outing_id=? AND user_id=?', (oid, target_id)).fetchone()
        if balance[0] or balance[1]:
            conn.execute('INSERT INTO daytrip_ledger VALUES(?,?,?,?,?,?,?,?,?)', (identifier(),oid,target_id,'reverse',-balance[0],-balance[1],reason,'D1',now()))
        conn.execute('UPDATE daytrip_participants SET points=0,provider_verified=0,confirmed_by=NULL,revoked=? WHERE outing_id=? AND user_id=?', (int(revoke), oid, target_id))
        # Consumed discounts remain financially immutable; corrections are explicit.
        conn.execute("UPDATE daytrip_redemptions SET adjustment_required=1,version=version+1 WHERE user_id=? AND status='redeemed' AND outing_id=? AND adjustment_required=0", (target_id,oid))
        conn.execute("UPDATE daytrip_redemptions SET status='cancelled',version=version+1 WHERE user_id=? AND status='reserved' AND outing_id=?", (target_id,oid))
        if balance[1]:
            self.correct_benefit_evidence(conn, target_id, oid)

    @staticmethod
    def eligible_entries(conn, uid, excluded_outing=None):
        return conn.execute('SELECT l.id,l.outing_id,l.eligible_points,l.created_at,o.ends_at FROM daytrip_ledger l JOIN daytrip_outings o ON o.id=l.outing_id WHERE l.user_id=? AND l.eligible_points!=0 AND (? IS NULL OR l.outing_id!=?) ORDER BY l.created_at,l.id', (uid,excluded_outing,excluded_outing)).fetchall()

    @staticmethod
    def invalid_reserved_evidence(held, entries, corrected_outing):
        conditions = json.loads(held['conditions_json'])
        qualification, evidence = conditions.get('rank_qualification'), conditions.get('rank_evidence')
        if qualification and evidence:
            if not any(item['outing_id'] == corrected_outing for item in evidence):
                return False
            # Re-evaluate exactly the frozen evidence at the held instant. The
            # present date and any later positive credits cannot change it.
            remaining = evidence_status(evidence, entries, datetime.fromisoformat(qualification['evaluated_at']))
            return remaining['lifetime_points'] <= 0 or remaining['rank'] < conditions['benefit']['min_rank']
        eligible = legacy_eligible_points([row for row in entries if row['outing_id'] != held['outing_id']], datetime.fromisoformat(held['created_at']))
        original = conditions['benefit']
        level = original['min_rank'] if original.get('rank_policy_version') == VERSION else LEGACY_LEVELS[original['min_rank']]
        return eligible <= 0 or eligible < THRESHOLDS[level - 1]

    def correct_benefit_evidence(self, conn, uid, corrected_outing):
        entries = self.eligible_entries(conn, uid)
        for held in conn.execute("SELECT * FROM daytrip_redemptions WHERE user_id=? AND status IN ('reserved','redeemed') AND outing_id!=?", (uid,corrected_outing)).fetchall():
            if not self.invalid_reserved_evidence(held, entries, corrected_outing):
                continue
            if held['status'] == 'reserved':
                conn.execute("UPDATE daytrip_redemptions SET status='cancelled',version=version+1 WHERE id=? AND status='reserved'", (held['id'],))
            elif not held['adjustment_required']:
                conn.execute('UPDATE daytrip_redemptions SET adjustment_required=1,version=version+1 WHERE id=?', (held['id'],))

    def cancel(self, uid, oid, data, participant_id=None):
        with self.db.transaction(True) as conn:
            row = self.access(conn, uid, oid, manage=participant_id != uid)
            self.version(row, data['version'])
            self.mutable(row)
            targets = [participant_id] if participant_id else [item[0] for item in conn.execute('SELECT user_id FROM daytrip_participants WHERE outing_id=?', (oid,))]
            for target in targets:
                self.person(conn, oid, target)
                self.reverse_person(conn, oid, target, data['reason'])
            if row['leader_id'] in targets and clock_now() < datetime.fromisoformat(row['starts_at']):
                conn.execute('UPDATE daytrip_outings SET leader_accepted=0 WHERE id=?', (oid,))
            # Withdrawing attendance also withdraws this witness's attestations.
            # The affected peers retain their own attendance claims and can be
            # confirmed again by another attendee; their own testimony remains.
            if participant_id:
                for dependent in conn.execute('SELECT user_id FROM daytrip_participants WHERE outing_id=? AND confirmed_by=? AND revoked=0', (oid,participant_id)).fetchall():
                    self.reverse_person(conn, oid, dependent['user_id'], '確認者の参加取消により再確認待ち', revoke=False)
            status = ('scheduled' if clock_now() < datetime.fromisoformat(row['starts_at']) else 'reporting') if participant_id else 'cancelled'
            conn.execute('UPDATE daytrip_outings SET status=?,version=version+1 WHERE id=?', (status, oid))
            self.event(conn, oid, uid, 'participant_cancelled' if participant_id else 'cancelled', {'participants': targets, 'reason': data['reason']})
            return self.current_out(conn, uid, oid)

    @staticmethod
    def balance(conn, uid, excluded_outing=None):
        return conn.execute('SELECT COALESCE(SUM(points),0) AS points,COALESCE(SUM(eligible_points),0) AS eligible_points FROM daytrip_ledger WHERE user_id=? AND (? IS NULL OR outing_id!=?)', (uid, excluded_outing, excluded_outing)).fetchone()

    @staticmethod
    def rank_states(conn, uid, excluded_outing=None, at=None):
        at = at or clock_now()
        # Aggregate every correction with its original outing BEFORE applying
        # the rolling window. Ledger insertion time is never an activity date.
        rows = conn.execute('SELECT o.ends_at,SUM(l.points) AS points,SUM(l.eligible_points) AS eligible_points FROM daytrip_ledger l JOIN daytrip_outings o ON o.id=l.outing_id WHERE l.user_id=? AND (? IS NULL OR l.outing_id!=?) GROUP BY l.outing_id,o.ends_at', (uid,excluded_outing,excluded_outing)).fetchall()
        return tuple(evaluate(sum(row[key] for row in rows), [(datetime.fromisoformat(row['ends_at']), row[key]) for row in rows], at) for key in ('points','eligible_points'))

    @staticmethod
    def benefit_out(conn, row, uid=None, staff=False):
        place = conn.execute('SELECT v.name AS provider_name,v.area,p.body FROM providers v JOIN provider_plans p ON p.provider_id=v.id WHERE p.id=? AND v.id=?', (row['plan_id'], row['provider_id'])).fetchone()
        details = dict(provider_name=place['provider_name'], area=place['area'],
                       plan_title=json.loads(place['body']).get('title', ''),
                       route_ids=[item[0] for item in conn.execute('SELECT route_id FROM daytrip_plan_routes WHERE plan_id=? ORDER BY route_id', (row['plan_id'],))]) if place else {}
        result = dict(row) | dict(min_rank=benefit_level(conn, row), rank_policy_version=VERSION,
                                 original_rank_policy=benefit_policy(conn, row), funding='provider', combinable=False) | details
        if uid is not None:
            result['zone_offer'] = personal_offer(conn, uid, row, json.loads(place['body'])['price_yen']) if place else None
        if staff:
            result['zone_policy'] = budget_status(conn, row['id'])
            result['zone_policy_configurable'] = can_configure(conn, row)
            result['zone_used_yen'] = used_yen(conn, row['id'])
        return result

    @staticmethod
    def redemption_out(row):
        result = {key: row[key] for key in ('id','benefit_id','outing_id','user_id','provider_id','status','version','original_yen','discount_yen','total_yen','adjustment_required','created_at')}
        result['adjustment_required'] = bool(result['adjustment_required'])
        return result

    def me(self, uid):
        with self.db.transaction() as conn:
            personal, eligible = self.rank_states(conn, uid)
            awarded = conn.execute("SELECT COUNT(*) FROM daytrip_participants p JOIN daytrip_outings o ON o.id=p.outing_id WHERE p.user_id=? AND p.points>0 AND o.status!='cancelled'", (uid,)).fetchone()[0]
            leaders = conn.execute("SELECT COUNT(*) FROM daytrip_participants p JOIN daytrip_outings o ON o.id=p.outing_id WHERE p.user_id=? AND p.points>0 AND p.full_route=1 AND o.leader_id=p.user_id AND o.status!='cancelled'", (uid,)).fetchone()[0]
            ledger = [dict(row) for row in conn.execute('SELECT id,outing_id,kind,points,eligible_points,reason,created_at FROM daytrip_ledger WHERE user_id=? ORDER BY created_at DESC,id DESC LIMIT 200', (uid,))]
            benefits = [self.benefit_out(conn, row, uid=uid) for row in conn.execute("SELECT b.* FROM daytrip_benefits b JOIN providers p ON p.id=b.provider_id JOIN provider_plans q ON q.id=b.plan_id WHERE b.status='published' AND b.ends_on>=? AND p.active=1 AND q.status='published' ORDER BY b.created_at DESC LIMIT 100", (clock_now().astimezone(JST).date().isoformat(),))]
            redemptions = [self.redemption_out(row) for row in conn.execute('SELECT * FROM daytrip_redemptions WHERE user_id=? ORDER BY created_at DESC LIMIT 100', (uid,))]
            return dict(points=personal['lifetime_points'], eligible_points=eligible['lifetime_points'], rank=personal['rank'],
                        eligible_rank=eligible['rank'], rank_status=personal, eligible_rank_status=eligible,
                        next_rank_points=personal['next_rank_points'], completed_count=awarded, leader_count=leaders,
                        ledger=ledger, benefits=benefits, redemptions=redemptions)

    def provider(self, uid):
        with self.db.transaction() as conn:
            providers = [row[0] for row in conn.execute('SELECT s.provider_id FROM provider_staff s JOIN providers p ON p.id=s.provider_id WHERE s.user_id=? AND s.active=1 AND p.active=1', (uid,))]
            result = dict(plans=[], links=[], outings=[], benefits=[], redemptions=[])
            for pid in providers:
                result['plans'].extend(self.market.plan_out(conn, row) for row in conn.execute('SELECT * FROM provider_plans WHERE provider_id=? ORDER BY updated_at DESC', (pid,)))
                result['links'].extend(dict(row) for row in conn.execute('SELECT l.plan_id,l.route_id FROM daytrip_plan_routes l JOIN provider_plans p ON p.id=l.plan_id WHERE p.provider_id=?', (pid,)))
                result['outings'].extend(self.out(conn,uid,row,True) for row in conn.execute("SELECT o.* FROM daytrip_outings o JOIN circle_provider_invitations i ON i.id=o.invitation_id JOIN travel_parties p ON p.id=o.circle_id WHERE o.provider_id=? AND i.status='accepted' AND p.status='open' ORDER BY o.starts_at DESC LIMIT 100", (pid,)))
                result['benefits'].extend(self.benefit_out(conn, row, staff=True) for row in conn.execute('SELECT * FROM daytrip_benefits WHERE provider_id=? ORDER BY created_at DESC LIMIT 100', (pid,)))
                result['redemptions'].extend(self.redemption_out(row) for row in conn.execute('SELECT * FROM daytrip_redemptions WHERE provider_id=? ORDER BY created_at DESC LIMIT 100', (pid,)))
            return result

    def link(self, uid, plan_id, route_id):
        with self.db.transaction(True) as conn:
            row = require(conn.execute('SELECT * FROM provider_plans WHERE id=?', (plan_id,)).fetchone())
            self.market.staff(conn, uid, row['provider_id'])
            if json.loads(row['body'])['nights'] != 0:
                raise HTTPException(409, '日帰りプランに経路を設定してください。')
            self.route(route_id)
            conn.execute('INSERT INTO daytrip_plan_routes VALUES(?,?,?,?) ON CONFLICT(plan_id) DO UPDATE SET route_id=excluded.route_id,updated_by=excluded.updated_by,updated_at=excluded.updated_at', (plan_id,route_id,uid,now()))
            return dict(plan_id=plan_id, route_id=route_id)

    def create_benefit(self, uid, data):
        if data.get('rank_policy_version', 'D1') == 'D1':
            data = data | {'min_rank': LEGACY_LEVELS[data['min_rank']]}
        with self.db.transaction(True) as conn:
            plan_row, plan = self.public_plan(conn, data['plan_id'])
            self.market.staff(conn, uid, plan_row['provider_id'])
            if plan['price_basis'] != 'per_person':
                raise HTTPException(409, '一人あたりの料金のプランだけに特典を設定できます。')
            if data['ends_on'] < clock_now().astimezone(JST).date().isoformat():
                raise HTTPException(422, 'これから利用できる期間を指定してください。')
            if conn.execute('SELECT COUNT(*) FROM daytrip_benefits WHERE provider_id=?', (plan_row['provider_id'],)).fetchone()[0] >= 100:
                raise HTTPException(409, '特典は事業者ごとに100件までです。')
            bid = identifier()
            keys = ('plan_id','title','min_rank','discount_type','discount_value','max_discount_yen','max_redemptions','starts_on','ends_on')
            conn.execute("INSERT INTO daytrip_benefits(id,provider_id,plan_id,title,min_rank,discount_type,discount_value,max_discount_yen,max_redemptions,starts_on,ends_on,status,created_at) VALUES(?,?,?,?,?,?,?,?,?,?,?,'published',?)", (bid,plan_row['provider_id'],*(data[key] for key in keys),now()))
            conn.execute('INSERT INTO settings(key,value) VALUES(?,?)', ('daytrip-benefit-rank:' + bid,VERSION))
            return self.benefit_out(conn, conn.execute('SELECT * FROM daytrip_benefits WHERE id=?', (bid,)).fetchone())

    def close_benefit(self, uid, bid, version):
        with self.db.transaction(True) as conn:
            row = require(conn.execute('SELECT * FROM daytrip_benefits WHERE id=?', (bid,)).fetchone())
            self.market.staff(conn, uid, row['provider_id'])
            self.version(row, version)
            conn.execute("UPDATE daytrip_benefits SET status='closed',version=version+1 WHERE id=?", (bid,))
            conn.execute("UPDATE daytrip_redemptions SET status='cancelled',version=version+1 WHERE benefit_id=? AND status='reserved'", (bid,))
            return self.benefit_out(conn, conn.execute('SELECT * FROM daytrip_benefits WHERE id=?', (bid,)).fetchone())

    def zone_policy(self, uid, bid, data):
        with self.db.transaction(True) as conn:
            row = require(conn.execute('SELECT * FROM daytrip_benefits WHERE id=?', (bid,)).fetchone())
            self.market.staff(conn, uid, row['provider_id'])
            self.version(row, data['version'])
            return configure(conn, row, data)

    def check_benefit(self, conn, uid, benefit, outing, check_rank=True, at=None):
        at = at or clock_now()
        self.mutable(outing)
        person = self.active_person(conn, outing, uid)
        if not person['accepted'] or outing['plan_id'] != benefit['plan_id']:
            raise HTTPException(409, '対象プランと開催への参加承諾を確認してください。')
        if benefit['status'] != 'published' or not benefit['starts_on'] <= outing['day'] <= benefit['ends_on']:
            raise HTTPException(409, 'この開催には特典の利用条件が合いません。')
        today = at.astimezone(JST).date().isoformat()
        if today > benefit['ends_on']:
            raise HTTPException(409, '特典の利用期間が終了しています。')
        if check_rank:
            _, eligible = self.rank_states(conn, uid, outing['id'], at)
            if eligible['lifetime_points'] <= 0 or eligible['rank'] < benefit_level(conn, benefit):
                raise HTTPException(409, '事業者が利用確認した過去の活動が特典対象階級の条件に達していません。')
        plan_row, plan = self.public_plan(conn, benefit['plan_id'])
        snapshot = json.loads(outing['plan_json'])
        if plan['price_basis'] != 'per_person' or snapshot['version'] != plan_row['version']:
            raise HTTPException(409, 'プランが変更されています。新しい条件で開催を準備してください。')
        return plan_row, plan

    def reserve(self, uid, bid, data):
        with self.db.transaction(True) as conn:
            outing = self.access(conn, uid, data['outing_id'])
            self.before_start(outing)
            benefit = require(conn.execute('SELECT * FROM daytrip_benefits WHERE id=?', (bid,)).fetchone())
            operation = 'daytrip:reserve:' + bid
            previous, fingerprint = self.market.replay(conn, uid, operation, data)
            if previous:
                return self.redemption_out(require(conn.execute('SELECT * FROM daytrip_redemptions WHERE id=? AND user_id=?', (previous,uid)).fetchone()))
            evaluated_at = clock_now()
            plan_row, plan = self.check_benefit(conn, uid, benefit, outing, at=evaluated_at)
            if conn.execute('SELECT 1 FROM daytrip_redemptions WHERE outing_id=? AND user_id=?', (outing['id'],uid)).fetchone():
                raise HTTPException(409, 'この開催の特典は確保済み、または取消済みです。')
            uses = conn.execute("SELECT COUNT(*) FROM daytrip_redemptions WHERE benefit_id=? AND status IN ('reserved','redeemed')", (bid,)).fetchone()[0]
            if uses >= benefit['max_redemptions']:
                raise HTTPException(409, 'この特典の利用枠は埋まっています。')
            original = plan['price_yen']
            # This quote and the subsequent insertion share BEGIN IMMEDIATE;
            # concurrent requests cannot both spend the same remaining budget.
            discount, zone_offer = reservation_discount(conn, uid, benefit, original)
            rid = identifier()
            _, qualified = self.rank_states(conn, uid, outing['id'], evaluated_at)
            conditions = dict(benefit=self.benefit_out(conn, benefit),rank_qualification=qualified,
                              rank_evidence=capture_evidence(self.eligible_entries(conn, uid, outing['id'])),
                              plan_version=plan_row['version'],price_note=plan['price_note'],price_scope=plan['price_scope'],price_basis=plan['price_basis'],
                              zone_offer=zone_offer)
            conn.execute("INSERT INTO daytrip_redemptions(id,benefit_id,outing_id,user_id,provider_id,status,original_yen,discount_yen,total_yen,conditions_json,created_at) VALUES(?,?,?,?,?,'reserved',?,?,?,?,?)", (rid,bid,outing['id'],uid,benefit['provider_id'],original,discount,original-discount,dump(conditions),now()))
            self.market.remember(conn, uid, operation, data, fingerprint, rid)
            self.event(conn, outing['id'], uid, 'benefit_reserved', {'redemption_id': rid})
            return self.redemption_out(conn.execute('SELECT * FROM daytrip_redemptions WHERE id=?', (rid,)).fetchone())

    def redemption(self, uid, rid, version, cancel=False):
        with self.db.transaction(True) as conn:
            row = require(conn.execute('SELECT * FROM daytrip_redemptions WHERE id=?', (rid,)).fetchone())
            if not cancel or row['user_id'] != uid:
                outing = self.access(conn, uid, row['outing_id'], provider=True)
            else:
                outing = self.access(conn, uid, row['outing_id'])
            self.version(row, version)
            if row['status'] != 'reserved':
                raise HTTPException(409, 'この特典の利用または取消は記録済みです。')
            if not cancel:
                self.after_end(outing)
                benefit = require(conn.execute('SELECT * FROM daytrip_benefits WHERE id=?', (row['benefit_id'],)).fetchone())
                self.check_benefit(conn, row['user_id'], benefit, outing, check_rank=False)
                person = self.person(conn, outing['id'], row['user_id'])
                if not person['confirmed_by'] or not person['provider_verified']:
                    raise HTTPException(409, '実参加と事業者の利用確認を先に行ってください。')
                if conn.execute('SELECT 1 FROM provider_staff WHERE provider_id=? AND user_id=?', (row['provider_id'],row['user_id'])).fetchone():
                    raise HTTPException(409, '自社スタッフの特典は処理できません。')
            conn.execute('UPDATE daytrip_redemptions SET status=?,version=version+1 WHERE id=?', ('cancelled' if cancel else 'redeemed', rid))
            self.event(conn, row['outing_id'], uid, 'benefit_cancelled' if cancel else 'benefit_redeemed', {'redemption_id':rid})
            return self.redemption_out(conn.execute('SELECT * FROM daytrip_redemptions WHERE id=?', (rid,)).fetchone())
