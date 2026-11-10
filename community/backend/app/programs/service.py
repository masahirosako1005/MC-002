import json
from datetime import UTC, datetime, timedelta, timezone

from fastapi import HTTPException

from ..database import identifier, now
from ..daytrip.service import Daytrip
from ..marketplace.service import Marketplace, conflict, dump
from ..service import require
from .catalog import PROGRAMS, plan_id

JST = timezone(timedelta(hours=9))
NOTICE = '登録は予約や決済ではありません。各回の日程・受入・料金は事業者との相談で確認してください。'


def clock_now():
    return datetime.now(UTC)


class Programs:
    def __init__(self, database):
        self.db = database
        self.market = Marketplace(database)
        self.daytrip = Daytrip(database)

    @staticmethod
    def definition(pid):
        return require(next((item for item in PROGRAMS if item['id'] == pid), None))

    def public(self, conn, pid):
        definition = self.definition(pid)
        provider = require(conn.execute('SELECT id,name FROM providers WHERE id=? AND active=1',
                                        (definition['provider_id'],)).fetchone())
        steps = []
        for order, (sid, title, purpose, _) in enumerate(definition['steps'], 1):
            row = require(conn.execute("SELECT p.* FROM provider_plans p JOIN daytrip_plan_routes r ON r.plan_id=p.id WHERE p.id=? AND p.provider_id=? AND p.status='published' AND r.route_id=?",
                (plan_id(pid, sid), provider['id'], definition['route_id'])).fetchone())
            body = json.loads(row['body'])
            if (body.get('nights'), body.get('price_basis'), body.get('price_scope')) != (0, 'per_person', 'plan_only'):
                raise HTTPException(404, '利用できる通う旅が見つかりません。')
            steps.append(dict(id=sid, order=order, title=title, purpose=purpose, plan_id=row['id'],
                              plan_title=body['title'], price_yen=body['price_yen'], route_id=definition['route_id']))
        return dict(id=pid, title=definition['title'], goal=definition['goal'], area='N西市', provider=dict(provider), available=True, unavailable_reason=None,
            recommended_interval=definition['recommended_interval'], steps=steps,
            total_price_yen=sum(step['price_yen'] for step in steps), price_basis='per_person', price_scope='plan_only',
            price_note='各回の一人料金の合計・割引前です。往復交通費は別途必要です。日程と予約は各回ごとに確認します。')

    @staticmethod
    def enrolled(conn, uid, pid):
        return require(conn.execute('SELECT * FROM program_enrollments WHERE user_id=? AND program_id=?', (uid, pid)).fetchone())

    @staticmethod
    def links(conn, uid, pid):
        return {row['step_id']: row['outing_id'] for row in conn.execute(
            'SELECT step_id,outing_id FROM program_step_links WHERE user_id=? AND program_id=?', (uid, pid))}

    def accessible(self, conn, uid, oid, step, provider):
        require(conn.execute('SELECT 1 FROM providers WHERE id=? AND active=1', (provider,)).fetchone())
        row = self.daytrip.access(conn, uid, oid)
        person = self.daytrip.active_person(conn, row, uid)
        if not person['accepted'] or row['plan_id'] != step['plan_id'] or row['provider_id'] != provider:
            raise HTTPException(404, 'この段階に使える参加承諾済みの開催が見つかりません。')
        require(conn.execute("SELECT 1 FROM circle_provider_invitations WHERE id=? AND provider_id=? AND status='accepted'",
                             (row['invitation_id'], provider)).fetchone())
        return row, person

    @staticmethod
    def completed(conn, row, person):
        witness = conn.execute('''SELECT 1 FROM daytrip_participants a JOIN users u ON u.id=a.user_id
            WHERE a.outing_id=? AND a.user_id=? AND a.user_id!=? AND a.accepted=1 AND a.claimed=1
            AND a.revoked=0 AND u.login_enabled=1''', (row['id'], person['confirmed_by'], person['user_id'])).fetchone()
        return (row['status'] in ('reporting', 'confirmed') and person['claimed'] and person['full_route']
                and person['provider_verified'] and witness is not None)

    def step_state(self, conn, uid, oid, step, provider):
        result = dict(step_id=step['id'], status='unplanned', outing_id=oid, has_link=oid is not None, reason=None)
        if oid is None:
            return result, None
        try:
            row, person = self.accessible(conn, uid, oid, step, provider)
        except HTTPException as exc:
            if exc.status_code != 404 and exc.status_code != 409:
                raise
            return result | dict(status='invalid', outing_id=None, reason='開催の参加・共有条件を確認できません。'), None
        ended = datetime.fromisoformat(row['ends_at'])
        if row['status'] == 'cancelled':
            return result | dict(status='invalid', reason='開催が取り消されています。'), ended.astimezone(JST).date()
        if ended > clock_now():
            return result | dict(status='planned', reason='予定です。実施後の確認で進捗に反映します。'), ended.astimezone(JST).date()
        done = self.completed(conn, row, person)
        return result | dict(status='completed' if done else 'awaiting_confirmation',
            reason=None if done else '全行程参加・仲間の確認・事業者の利用確認が必要です。'), ended.astimezone(JST).date()

    def progress(self, conn, uid, program, enrollment):
        mapping = self.links(conn, uid, program['id']) if enrollment['status'] == 'active' else {}
        result, previous_day, preceding_done = [], None, True
        for step in program['steps']:
            state, day = self.step_state(conn, uid, mapping.get(step['id']), step, program['provider']['id'])
            if day is not None and previous_day is not None and day <= previous_day:
                state.update(status='invalid', reason='段階ごとに順番の異なる別日の開催が必要です。')
            if state['status'] == 'completed' and not preceding_done:
                state.update(status='awaiting_confirmation', reason='前の段階の利用確認を先に完了してください。')
            preceding_done = preceding_done and state['status'] == 'completed'
            previous_day = day if day is not None else previous_day
            result.append(state)
        count = sum(row['status'] == 'completed' for row in result)
        status = 'completed' if count == len(result) else enrollment['status']
        return dict(version=enrollment['version'], status=status, completed_count=count, total_steps=len(result), steps=result)

    def catalogue(self, uid):
        with self.db.transaction() as conn:
            items = []
            for definition in PROGRAMS:
                row = conn.execute('SELECT * FROM program_enrollments WHERE user_id=? AND program_id=?', (uid, definition['id'])).fetchone()
                try:
                    item = self.public(conn, definition['id'])
                except HTTPException as exc:
                    if exc.status_code != 404:
                        raise
                    if row is None:
                        continue
                    item = self.unavailable(row)
                items.append(item | dict(enrollment=self.progress(conn, uid, item, row) if row else None))
            return dict(items=items, notice=NOTICE)

    @staticmethod
    def unavailable(enrollment):
        return json.loads(enrollment['snapshot']) | dict(available=False,
            unavailable_reason='現在は受付を停止しています。登録の取消と開催の紐付け解除はできます。',
            price_note='登録時の参考料金です。現在の販売価格・受入を示しません。')

    @staticmethod
    def event(conn, uid, pid, kind, body):
        conn.execute('INSERT INTO program_events VALUES(?,?,?,?,?,?)', (identifier(), uid, pid, kind, dump(body), now()))

    def enroll(self, uid, pid, data):
        with self.db.transaction(True) as conn:
            program = self.public(conn, pid)
            previous, digest = self.market.replay(conn, uid, 'program:enroll:' + pid, data)
            row = conn.execute('SELECT * FROM program_enrollments WHERE user_id=? AND program_id=?', (uid, pid)).fetchone()
            if not previous:
                if row is None:
                    conn.execute('INSERT INTO program_enrollments(user_id,program_id,created_at,snapshot) VALUES(?,?,?,?)', (uid, pid, now(), dump(program)))
                elif row['status'] == 'cancelled':
                    conn.execute("UPDATE program_enrollments SET status='active',version=version+1,snapshot=? WHERE user_id=? AND program_id=?", (dump(program), uid, pid))
                self.market.remember(conn, uid, 'program:enroll:' + pid, data, digest, pid)
                self.event(conn, uid, pid, 'enrolled', {})
            return self.progress(conn, uid, program, self.enrolled(conn, uid, pid))

    def cancel(self, uid, pid, data):
        with self.db.transaction(True) as conn:
            row = self.enrolled(conn, uid, pid)
            program = json.loads(row['snapshot'])
            previous, digest = self.market.replay(conn, uid, 'program:cancel:' + pid, data)
            if not previous:
                if row['version'] != data['version']:
                    conflict()
                conn.execute('DELETE FROM program_step_links WHERE user_id=? AND program_id=?', (uid, pid))
                conn.execute("UPDATE program_enrollments SET status='cancelled',version=version+1 WHERE user_id=? AND program_id=?", (uid, pid))
                self.market.remember(conn, uid, 'program:cancel:' + pid, data, digest, pid)
                self.event(conn, uid, pid, 'cancelled', {})
            return self.progress(conn, uid, program, self.enrolled(conn, uid, pid))

    def chronological(self, conn, uid, program, target, row):
        start, end = (datetime.fromisoformat(row[key]).astimezone(JST) for key in ('starts_at', 'ends_at'))
        if start >= end or start.date() != end.date():
            raise HTTPException(409, '同じ日の中で実施する開催を選んでください。')
        duplicates = conn.execute('SELECT program_id,step_id FROM program_step_links WHERE user_id=? AND outing_id=?', (uid, row['id'])).fetchone()
        if duplicates and (duplicates['program_id'], duplicates['step_id']) != (program['id'], target['id']):
            raise HTTPException(409, 'この開催はすでに別の段階に使っています。')
        mapping = self.links(conn, uid, program['id'])
        for step in program['steps']:
            if step['id'] == target['id'] or step['id'] not in mapping:
                continue
            linked = conn.execute('SELECT ends_at FROM daytrip_outings WHERE id=?', (mapping[step['id']],)).fetchone()
            other_day = datetime.fromisoformat(linked['ends_at']).astimezone(JST).date()
            earlier = other_day < end.date() if step['order'] < target['order'] else other_day > end.date()
            if not earlier:
                raise HTTPException(409, '各段階は順番に、別の日の開催を選んでください。')

    def link(self, uid, pid, sid, data):
        with self.db.transaction(True) as conn:
            enrollment = self.enrolled(conn, uid, pid)
            program = self.public(conn, pid) if data['outing_id'] is not None else json.loads(enrollment['snapshot'])
            step = require(next((row for row in program['steps'] if row['id'] == sid), None))
            if enrollment['version'] != data['version'] or enrollment['status'] != 'active':
                conflict()
            if data['outing_id'] is not None:
                outing, _ = self.accessible(conn, uid, data['outing_id'], step, program['provider']['id'])
                if outing['status'] == 'cancelled':
                    raise HTTPException(409, '中止した開催は選べません。')
                self.chronological(conn, uid, program, step, outing)
            conn.execute('DELETE FROM program_step_links WHERE user_id=? AND program_id=? AND step_id=?', (uid, pid, sid))
            if data['outing_id'] is not None:
                conn.execute('INSERT INTO program_step_links VALUES(?,?,?,?,?)', (uid, pid, sid, data['outing_id'], now()))
            conn.execute('UPDATE program_enrollments SET version=version+1 WHERE user_id=? AND program_id=?', (uid, pid))
            self.event(conn, uid, pid, 'linked', dict(step_id=sid, outing_id=data['outing_id']))
            return self.progress(conn, uid, program, self.enrolled(conn, uid, pid))

    def outings(self, uid, pid):
        with self.db.transaction() as conn:
            program, items = self.public(conn, pid), []
            for step in program['steps']:
                rows = conn.execute('''SELECT o.id FROM daytrip_outings o JOIN daytrip_participants a ON a.outing_id=o.id
                    WHERE a.user_id=? AND o.plan_id=? ORDER BY o.starts_at DESC LIMIT 100''', (uid, step['plan_id']))
                for row in rows:
                    state, _ = self.step_state(conn, uid, row['id'], step, program['provider']['id'])
                    if state['status'] == 'invalid':
                        continue
                    outing = conn.execute('SELECT id,title,starts_at,ends_at,plan_id,status FROM daytrip_outings WHERE id=?', (row['id'],)).fetchone()
                    items.append(dict(outing))
            return dict(items=items)
