import hashlib
import json
import re

from fastapi import HTTPException

from ..database import TAGS, identifier, now
from ..image_guidance import IMAGE_PROCESSING
from ..service import member, require
from .schedules import schedule_fields, schedule_match, schedule_state


def dump(value):
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(',', ':'))


def conflict():
    raise HTTPException(409, '内容が更新されています。開き直して確認してください。')


class Marketplace:
    def __init__(self, database):
        self.db = database

    def staff(self, conn, uid, provider_id):
        return require(conn.execute('SELECT s.* FROM provider_staff s JOIN providers p ON p.id=s.provider_id WHERE s.user_id=? AND s.provider_id=? AND s.active=1 AND p.active=1', (uid, provider_id)).fetchone())

    def party(self, conn, uid, pid, representative=False):
        row = require(conn.execute('SELECT p.* FROM travel_parties p JOIN travel_party_members m ON m.party_id=p.id WHERE p.id=? AND m.user_id=?', (pid, uid)).fetchone())
        member(conn, uid, row['community_id'])
        if row['ko_group_id']:
            require(conn.execute('SELECT 1 FROM group_members WHERE group_id=? AND user_id=?', (row['ko_group_id'], uid)).fetchone())
        if representative and row['representative_id'] != uid:
            raise HTTPException(404, '計画が見つかりません。')
        if representative and row['status'] != 'open':
            raise HTTPException(409, 'この旅行計画は閉じています。')
        return row

    def party_out(self, conn, uid, row):
        req = conn.execute('SELECT body,version FROM travel_requirements WHERE party_id=?', (row['id'],)).fetchone()
        count = conn.execute("SELECT COUNT(*) FROM travel_party_members pm JOIN users u ON u.id=pm.user_id JOIN memberships m ON m.user_id=pm.user_id AND m.community_id=? WHERE pm.party_id=? AND m.status='active' AND u.login_enabled=1", (row['community_id'], row['id'])).fetchone()[0]
        selection = conn.execute("SELECT c.id FROM consultations c JOIN plan_selections s ON s.id=c.selection_id WHERE s.party_id=? AND s.status='active'", (row['id'],)).fetchone()
        return dict(id=row['id'], community_id=row['community_id'], title=row['title'], representative_id=row['representative_id'], can_manage=row['representative_id']==uid, active_account_count=count, status=row['status'], requirements=({**json.loads(req['body']), 'version':req['version']} if req else None), consultation_id=selection['id'] if selection else None)

    def capabilities(self, uid):
        with self.db.transaction() as conn:
            rows = conn.execute('SELECT p.id,p.name,p.area FROM providers p JOIN provider_staff s ON s.provider_id=p.id WHERE s.user_id=? AND s.active=1 AND p.active=1', (uid,))
            return {'providers':[dict(r) for r in rows], 'traveler':True,
                    'hub':{'image_model':IMAGE_PROCESSING['name'], 'image_mode':IMAGE_PROCESSING['mode'],
                           'image_method':IMAGE_PROCESSING['method'], 'inference_enabled':False, 'external_ai_enabled':False,
                           'condition_method':'ローカルの定型案内・確認付き条件整理', 'recommendation_method':'人数・泊数・予算と公開カタログの照合'}}

    def providers(self, uid, pid=None):
        with self.db.transaction() as conn:
            if pid:
                return dict(require(conn.execute('SELECT id,name,description,area FROM providers WHERE id=? AND active=1', (pid,)).fetchone()))
            return {'items':[dict(r) for r in conn.execute('SELECT id,name,description,area FROM providers WHERE active=1 ORDER BY id')]}

    def plan_out(self, conn, row):
        provider = require(conn.execute('SELECT id,name,area FROM providers WHERE id=?', (row['provider_id'],)).fetchone())
        body = json.loads(row['body'])
        return {**body, **schedule_fields(body), 'id':row['id'], 'provider':dict(provider), 'status':row['status'], 'version':row['version'], 'source_note':'架空のローカル企画素材。予約・空席・営業は未確認。'}

    def plans(self, uid, plan_id=None, provider_id=None, mine=False):
        with self.db.transaction() as conn:
            if plan_id:
                row = require(conn.execute('SELECT p.* FROM provider_plans p JOIN providers v ON v.id=p.provider_id WHERE p.id=? AND v.active=1', (plan_id,)).fetchone())
                if row['status'] != 'published':
                    self.staff(conn, uid, row['provider_id'])
                return self.plan_out(conn, row)
            if mine:
                self.staff(conn, uid, provider_id)
            query = 'SELECT p.* FROM provider_plans p JOIN providers v ON v.id=p.provider_id WHERE v.active=1'
            args = []
            if not mine:
                query += " AND p.status='published'"
            if provider_id:
                query += ' AND p.provider_id=?'
                args.append(provider_id)
            plans=[]
            for row in conn.execute(query+' ORDER BY p.id',args):
                plan=self.plan_out(conn,row)
                if mine or schedule_state(plan) not in ('ended','invalid'):
                    plans.append(plan)
                if len(plans)>=100:
                    break
            return {'items':plans}

    def save_plan(self, uid, provider_id, data, plan_id=None):
        with self.db.transaction(True) as conn:
            if plan_id:
                row = require(conn.execute('SELECT * FROM provider_plans WHERE id=?', (plan_id,)).fetchone())
                provider_id = row['provider_id']
                self.staff(conn, uid, provider_id)
                if row['version'] != data['version']:
                    conflict()
                version = row['version'] + 1
            else:
                self.staff(conn, uid, provider_id)
                if data['version'] != 0:
                    conflict()
                plan_id, version = identifier(), 1
            body = {k:v for k,v in data.items() if k not in ('version','status')}
            conn.execute('INSERT INTO provider_plans VALUES(?,?,?,?,?,?) ON CONFLICT(id) DO UPDATE SET body=excluded.body,status=excluded.status,version=excluded.version,updated_at=excluded.updated_at', (plan_id, provider_id, dump(body), data['status'], version, now()))
            return self.plan_out(conn, conn.execute('SELECT * FROM provider_plans WHERE id=?', (plan_id,)).fetchone())

    def parties(self, uid, pid=None):
        with self.db.transaction() as conn:
            if pid:
                return self.party_out(conn, uid, self.party(conn, uid, pid))
            rows = conn.execute("SELECT p.* FROM travel_parties p JOIN travel_party_members pm ON pm.party_id=p.id JOIN memberships m ON m.user_id=pm.user_id AND m.community_id=p.community_id WHERE pm.user_id=? AND m.status='active' ORDER BY p.created_at DESC LIMIT 100", (uid,)).fetchall()
            return {'items':[self.party_out(conn, uid, self.party(conn, uid, r['id'])) for r in rows]}

    def create_party(self, uid, cid, data):
        with self.db.transaction(True) as conn:
            member(conn, uid, cid)
            gid = data['ko_group_id']
            people = set(data['member_ids']) | {uid}
            if not gid and people != {uid}:
                raise HTTPException(422, 'メンバーを加える場合は成立した講を選んでください。')
            if gid:
                require(conn.execute('SELECT 1 FROM ko_groups WHERE id=? AND community_id=?', (gid, cid)).fetchone())
            for person in people:
                member(conn, person, cid)
                require(conn.execute('SELECT 1 FROM users WHERE id=? AND login_enabled=1', (person,)).fetchone())
                if gid:
                    require(conn.execute('SELECT 1 FROM group_members WHERE group_id=? AND user_id=?', (gid, person)).fetchone())
            pid = identifier()
            conn.execute("INSERT INTO travel_parties VALUES(?,?,?,?,?,'open',?)", (pid,cid,gid,uid,data['title'],now()))
            conn.executemany('INSERT INTO travel_party_members VALUES(?,?)', [(pid, person) for person in sorted(people)])
            return self.party_out(conn, uid, self.party(conn, uid, pid))

    def requirements(self, uid, pid, data):
        with self.db.transaction(True) as conn:
            row = self.party(conn, uid, pid, True)
            old = conn.execute('SELECT version FROM travel_requirements WHERE party_id=?', (pid,)).fetchone()
            version = old['version'] if old else 0
            if version != data['version']:
                conflict()
            body = {k:v for k,v in data.items() if k != 'version'}
            conn.execute('INSERT INTO travel_requirements VALUES(?,?,?,?,?) ON CONFLICT(party_id) DO UPDATE SET body=excluded.body,version=excluded.version,confirmed_by=excluded.confirmed_by,confirmed_at=excluded.confirmed_at', (pid,dump(body),version+1,uid,now()))
            return self.party_out(conn, uid, row)

    def replay(self, conn, uid, operation, data):
        key = data['client_request_id']
        fingerprint = hashlib.sha256(dump(data).encode()).hexdigest()
        row = conn.execute('SELECT * FROM operation_keys WHERE actor_id=? AND operation=? AND request_key=?', (uid,operation,key)).fetchone()
        if row and row['payload_hash'] != fingerprint:
            conflict()
        return (row['result_id'] if row else None), fingerprint

    def remember(self, conn, uid, operation, data, fingerprint, result_id):
        conn.execute('INSERT INTO operation_keys VALUES(?,?,?,?,?)', (uid,operation,data['client_request_id'],fingerprint,result_id))

    def message_out(self, conn, row):
        name = require(conn.execute('SELECT name FROM users WHERE id=?', (row['author_id'],)).fetchone())['name']
        return {'id':row['id'], 'author_name':name, 'body':row['body'], 'created_at':row['created_at']}

    def messages(self, uid, scope, scope_id, data=None):
        table, column = ('party_messages','party_id') if scope == 'party' else ('consultation_messages','consultation_id')
        with self.db.transaction(bool(data)) as conn:
            row = self.party(conn, uid, scope_id) if scope == 'party' else self.consultation(conn, uid, scope_id)
            if data is None:
                messages = conn.execute(f'SELECT * FROM {table} WHERE {column}=? ORDER BY created_at DESC,id DESC LIMIT 100', (scope_id,)).fetchall()
                return {'items':[self.message_out(conn, r) for r in reversed(messages)]}
            operation = scope + ':message:' + scope_id
            previous, fingerprint = self.replay(conn,uid,operation,data)
            if previous:
                return self.message_out(conn, require(conn.execute(f'SELECT * FROM {table} WHERE id=?', (previous,)).fetchone()))
            if row['status'] != 'open':
                raise HTTPException(409, 'この相談は閉じています。')
            mid = identifier()
            conn.execute(f'INSERT INTO {table} VALUES(?,?,?,?,?)', (mid,scope_id,uid,data['body'],now()))
            self.remember(conn,uid,operation,data,fingerprint,mid)
            return self.message_out(conn,conn.execute(f'SELECT * FROM {table} WHERE id=?', (mid,)).fetchone())

    def draft(self, uid, pid, data):
        with self.db.transaction(True) as conn:
            self.party(conn,uid,pid)
            results = []
            for mid in dict.fromkeys(data['message_ids']):
                msg = require(conn.execute('SELECT body FROM party_messages WHERE id=? AND party_id=?', (mid,pid)).fetchone())
                text = msg['body']
                fields = {}
                for key,pattern in [('planned_people',r'(\d+)\s*人'),('nights',r'(\d+)\s*泊')]:
                    matches = re.finditer(pattern,text)
                    values = sorted({int(m.group(1)) for m in matches if key != 'planned_people' or not re.match(r'\s*(?:あたり|当たり|につき|\d+\s*万?円)',text[m.end():])})
                    if values:
                        fields[key] = values
                money = sorted({int(v) * (10000 if unit else 1) for v,unit in re.findall(r'(\d+)\s*(万)?円',text)})
                if money:
                    fields['budget_yen'] = money
                if fields:
                    results.append({'message_id':mid,'candidates':fields,'needs_confirmation':True})
            result = {'id':identifier(),'method':'numeric-rules-v1','candidates':results,'warning':'人数・泊数・金額の候補です。否定・引用・変更や予算の単位/範囲は自動確定しません。条件欄で確認してください。','status':'needs_confirmation'}
            conn.execute('INSERT INTO condition_drafts VALUES(?,?,?,?)', (result['id'],pid,dump(result),now()))
            return result

    def match(self, req, plan):
        reasons, excluded, unknown = [], [], ['営業・空席は未確認', '移動時間・交通費は未確認']
        _, schedule_reasons, schedule_excluded, schedule_unknown = schedule_match(plan,req.get('date_start'))
        reasons.extend(schedule_reasons)
        excluded.extend(schedule_excluded)
        unknown.extend(schedule_unknown)
        people = req['planned_people']
        if plan['min_people'] <= people <= plan['max_people']:
            reasons.append(f"予定{people}人が受入人数の範囲内")
        else:
            excluded.append('予定人数がプランの受入範囲外')
        if req['nights'] == plan['nights']:
            reasons.append(f"{req['nights']}泊{req['nights']+1}日の行程")
        else:
            excluded.append('泊数が一致しない')
        total = plan['price_yen'] * (people if plan['price_basis']=='per_person' else 1)
        if req['budget_yen'] is None:
            unknown.append('予算が未確認')
        elif req['budget_scope'] != plan['price_scope']:
            unknown.append('予算と価格に含む範囲が異なるため比較できない')
        else:
            budget = req['budget_yen'] * (people if req['budget_basis']=='per_person' else 1)
            if total <= budget:
                reasons.append('同じ費用範囲の概算が予算以内')
            else:
                excluded.append('同じ費用範囲の概算が予算を超える')
        if not req['date_start']:
            unknown.append('希望日が未確認')
        else:
            unknown.append('希望日の営業・空席は未確認')
        tags = sorted(set(req['interests']) & set(plan['tags']))
        if tags:
            reasons.append('共有した関心: ' + '・'.join(TAGS[t] for t in tags))
        elif not req['interests']:
            unknown.append('関心が未確認')
        return {'eligible':not excluded,'match_status':'excluded' if excluded else 'needs_confirmation','reasons':reasons,'excluded_reasons':excluded,'unknowns':unknown,'common_tags':tags,'estimated_total_yen':total}

    def recommendations(self, uid, pid, version):
        with self.db.transaction(True) as conn:
            self.party(conn,uid,pid)
            row = require(conn.execute('SELECT * FROM travel_requirements WHERE party_id=?', (pid,)).fetchone())
            if row['version'] != version:
                conflict()
            req = json.loads(row['body'])
            items = []
            for row in conn.execute("SELECT p.* FROM provider_plans p JOIN providers v ON v.id=p.provider_id WHERE p.status='published' AND v.active=1 ORDER BY p.id"):
                plan = self.plan_out(conn,row)
                items.append({'plan':plan,**self.match(req,plan)})
            items.sort(key=lambda item:(not item['eligible'],-len(item['common_tags']),item['plan']['id']))
            result = {'id':identifier(),'requirements_version':version,'method':'deterministic-constraints-v1','items':items}
            conn.execute('INSERT INTO recommendation_runs VALUES(?,?,?,?)',(result['id'],pid,dump(result),now()))
            return result

    def preview(self, conn, uid, pid, data):
        self.party(conn,uid,pid,True)
        requirements = require(conn.execute('SELECT * FROM travel_requirements WHERE party_id=?',(pid,)).fetchone())
        row = require(conn.execute("SELECT p.* FROM provider_plans p JOIN providers v ON v.id=p.provider_id WHERE p.id=? AND p.status='published' AND v.active=1",(data['plan_id'],)).fetchone())
        if requirements['version'] != data['requirements_version'] or row['version'] != data['plan_version']:
            conflict()
        req, plan = json.loads(requirements['body']), self.plan_out(conn,row)
        match = self.match(req,plan)
        if not match['eligible']:
            raise HTTPException(409,'人数・泊数・予算の条件が合いません。条件かプランを見直してください。')
        shared = {key:req[key] for key in ('planned_people','nights','budget_yen','budget_basis','budget_scope','date_start')}
        return {'plan':plan,'shared_conditions':shared,'match':match,'notice':'この条件と入力した相談文、相談室での表示名を選択先に共有します。元の写真・内部会話・個人の好みは共有しません。'}

    def selection_preview(self, uid,pid,data):
        with self.db.transaction() as conn:
            return self.preview(conn,uid,pid,data)

    def select(self,uid,pid,data):
        with self.db.transaction(True) as conn:
            self.party(conn,uid,pid,True)
            from ..circles.guards import reject_direct_selection
            reject_direct_selection(conn,pid)
            operation='selection:'+pid
            previous,fingerprint=self.replay(conn,uid,operation,data)
            if previous:
                return self.consultation_out(conn,uid,self.consultation(conn,uid,previous))
            preview=self.preview(conn,uid,pid,data)
            old=conn.execute("SELECT id FROM plan_selections WHERE party_id=? AND status='active'",(pid,)).fetchone()
            if old:
                conn.execute("UPDATE consultations SET status='closed',version=version+1 WHERE selection_id=?",(old['id'],))
                conn.execute("UPDATE plan_selections SET status='closed' WHERE id=?",(old['id'],))
            sid,cid=identifier(),identifier()
            snapshot={'plan':preview['plan'],'shared_conditions':preview['shared_conditions'],'share_note':data['share_note'],'requirements_version':data['requirements_version'],'unknowns':preview['match']['unknowns']}
            conn.execute("INSERT INTO plan_selections VALUES(?,?,?,?,?,?,'active',?)",(sid,pid,data['plan_id'],preview['plan']['provider']['id'],dump(snapshot),uid,now()))
            conn.execute("INSERT INTO consultations(id,selection_id,status,created_at) VALUES(?,?,'open',?)",(cid,sid,now()))
            self.remember(conn,uid,operation,data,fingerprint,cid)
            return self.consultation_out(conn,uid,self.consultation(conn,uid,cid))

    def consultation(self,conn,uid,cid):
        row=require(conn.execute('SELECT c.*,s.party_id,s.provider_id,s.snapshot FROM consultations c JOIN plan_selections s ON s.id=c.selection_id WHERE c.id=?',(cid,)).fetchone())
        from ..circles.guards import require_active_shared_room
        require_active_shared_room(conn,cid)
        staff=conn.execute('SELECT 1 FROM provider_staff s JOIN providers p ON p.id=s.provider_id WHERE s.provider_id=? AND s.user_id=? AND s.active=1 AND p.active=1',(row['provider_id'],uid)).fetchone()
        if not staff:
            self.party(conn,uid,row['party_id'])
        return row

    def consultation_out(self,conn,uid,row):
        staff=conn.execute('SELECT 1 FROM provider_staff s JOIN providers p ON p.id=s.provider_id WHERE s.user_id=? AND s.provider_id=? AND s.active=1 AND p.active=1',(uid,row['provider_id'])).fetchone()
        representative=conn.execute('SELECT 1 FROM travel_parties WHERE id=? AND representative_id=?',(row['party_id'],uid)).fetchone()
        return {'id':row['id'],'status':row['status'],'version':row['version'],'selection':json.loads(row['snapshot']),'can_close':bool(staff or representative),'created_at':row['created_at']}

    def consultations(self,uid,cid=None):
        with self.db.transaction() as conn:
            if cid:
                return self.consultation_out(conn,uid,self.consultation(conn,uid,cid))
            ids=conn.execute("SELECT DISTINCT c.id FROM consultations c JOIN plan_selections s ON s.id=c.selection_id JOIN travel_parties p ON p.id=s.party_id LEFT JOIN provider_staff st ON st.provider_id=s.provider_id AND st.user_id=? AND st.active=1 LEFT JOIN travel_party_members tm ON tm.party_id=p.id AND tm.user_id=? LEFT JOIN memberships m ON m.community_id=p.community_id AND m.user_id=? AND m.status='active' WHERE st.user_id IS NOT NULL OR (tm.user_id IS NOT NULL AND m.user_id IS NOT NULL) ORDER BY c.created_at DESC LIMIT 100",(uid,uid,uid)).fetchall()
            items=[]
            for row in ids:
                try:
                    items.append(self.consultation_out(conn,uid,self.consultation(conn,uid,row['id'])))
                except HTTPException as exc:
                    if exc.status_code != 404:
                        raise
            return {'items':items}

    def close(self,uid,cid,version):
        with self.db.transaction(True) as conn:
            row=self.consultation(conn,uid,cid)
            from ..circles.guards import reject_direct_close
            reject_direct_close(conn,cid)
            result=self.consultation_out(conn,uid,row)
            if not result['can_close']:
                raise HTTPException(404,'相談が見つかりません。')
            if row['version'] != version:
                conflict()
            conn.execute("UPDATE consultations SET status='closed',version=version+1 WHERE id=?",(cid,))
            conn.execute("UPDATE plan_selections SET status='closed' WHERE id=?",(row['selection_id'],))
            return self.consultation_out(conn,uid,self.consultation(conn,uid,cid))

    def close_party(self,uid,pid):
        with self.db.transaction(True) as conn:
            self.party(conn,uid,pid,True)
            conn.execute("UPDATE consultations SET status='closed',version=version+1 WHERE selection_id IN (SELECT id FROM plan_selections WHERE party_id=? AND status='active')",(pid,))
            conn.execute("UPDATE plan_selections SET status='closed' WHERE party_id=? AND status='active'",(pid,))
            conn.execute("UPDATE travel_parties SET status='closed' WHERE id=?",(pid,))
            return self.party_out(conn,uid,conn.execute('SELECT * FROM travel_parties WHERE id=?',(pid,)).fetchone())
