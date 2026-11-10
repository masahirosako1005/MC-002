import json
from datetime import datetime, timedelta, timezone

from fastapi import HTTPException

from ..database import identifier, now
from ..marketplace.service import Marketplace, conflict, dump
from ..service import require, user_out
from .aggregate import current_participants, effective, public_summary, state
from .extraction import METHOD, NOTICE, PURPOSE, extract

JST=timezone(timedelta(hours=9))


class Reflections:
    def __init__(self,database):
        self.db=database
        self.market=Marketplace(database)

    def traveler(self,conn,uid,pid,provider_id=None,representative=False):
        party=self.market.party(conn,uid,pid)
        if representative and party['representative_id']!=uid:
            raise HTTPException(404,'振り返りを管理できる代表者ではありません。')
        if provider_id and conn.execute('SELECT 1 FROM provider_staff WHERE provider_id=? AND user_id=?',(provider_id,uid)).fetchone():
            raise HTTPException(404,'旅行者の振り返りには参加できません。')
        return party

    def access(self,conn,uid,rid,representative=False):
        row=require(conn.execute('SELECT * FROM reflection_sessions WHERE id=?',(rid,)).fetchone())
        self.traveler(conn,uid,row['party_id'],row['provider_id'],representative)
        if uid not in json.loads(row['participants_json']):
            raise HTTPException(404,'この振り返りの対象者ではありません。')
        return row

    @staticmethod
    def summary(conn,row):
        status=state(conn,row)
        return dict(id=row['id'],circle_id=row['party_id'],provider=dict(conn.execute('SELECT id,name,area FROM providers WHERE id=?',(row['provider_id'],)).fetchone()),
                    ended_on=row['ended_on'],trip_finished=bool(row['trip_finished']),version=row['version'],epoch=row['epoch'],
                    **{key:status[key] for key in ('participant_set_current','ready_for_analysis','target_count','usage_confirmed_count','consented_count')})

    def message_out(self,conn,row,uid,reflection):
        ready=state(conn,reflection)['ready_for_analysis']
        values,automatic=effective(row) if ready else ([],None)
        if not ready:
            extraction=dict(status='waiting',reason='全対象者の実利用申告・同意と対象者の一致を確認するまで解析しません。',proposed=[],effective=[],can_correct=False)
        elif not automatic or not automatic['eligible']:
            extraction=dict(status='excluded',reason=automatic['reason'] if automatic else '解析できる発言がありません。',proposed=automatic['values'] if automatic else [],effective=[],can_correct=False)
        else:
            corrected=row['override_json'] is not None and row['override_source_version']==row['source_version']
            extraction=dict(status='author_corrected' if corrected else 'auto_included',reason=automatic['reason'],proposed=automatic['values'],effective=values,can_correct=row['author_id']==uid)
        extraction['source_version']=row['source_version']
        return dict(id=row['id'],author=user_out(conn.execute('SELECT * FROM users WHERE id=?',(row['author_id'],)).fetchone()),is_mine=row['author_id']==uid,
                    body=row['body'],version=row['version'],source_version=row['source_version'],created_at=row['created_at'],extraction=extraction)

    def detail(self,conn,uid,row):
        status=state(conn,row)
        participants=[dict(user=user_out(conn.execute('SELECT * FROM users WHERE id=?',(p['user_id'],)).fetchone()),used_service=bool(p['used_service']),consented=bool(p['consented'])) for p in status['participants']]
        mine=require(next((p for p in status['participants'] if p['user_id']==uid),None))
        party=conn.execute('SELECT representative_id FROM travel_parties WHERE id=?',(row['party_id'],)).fetchone()
        messages=[self.message_out(conn,message,uid,row) for message in conn.execute('SELECT * FROM reflection_messages WHERE reflection_id=? AND epoch=? AND deleted=0 ORDER BY created_at,id LIMIT 100',(row['id'],row['epoch']))]
        return dict(**self.summary(conn,row),participants=participants,my_state=dict(used_service=bool(mine['used_service']),consented=bool(mine['consented']),version=mine['version']),
                    messages=messages,method=METHOD,usage_notice=NOTICE,consent_purpose=PURPOSE,can_manage=party['representative_id']==uid)

    @staticmethod
    def earliest(invitation):
        shared=json.loads(invitation['snapshot'])['shared_conditions']
        accepted=datetime.fromisoformat(invitation['accepted_at']).astimezone(JST).date().isoformat()
        return max(accepted,shared.get('date_start') or accepted)

    def options(self,uid,pid):
        with self.db.transaction() as conn:
            self.traveler(conn,uid,pid)
            items=[]
            seen=set()
            for row in conn.execute('SELECT * FROM circle_provider_invitations WHERE party_id=? AND accepted_at IS NOT NULL ORDER BY created_at DESC,id',(pid,)):
                if row['provider_id'] in seen or conn.execute('SELECT 1 FROM provider_staff WHERE provider_id=? AND user_id=?',(row['provider_id'],uid)).fetchone():
                    continue
                seen.add(row['provider_id'])
                items.append(dict(invitation_id=row['id'],provider=dict(conn.execute('SELECT id,name,area FROM providers WHERE id=?',(row['provider_id'],)).fetchone()),plan_title=json.loads(row['snapshot'])['plan']['title'],earliest_end_on=self.earliest(row)))
            reflections=[self.summary(conn,row) for row in conn.execute('SELECT * FROM reflection_sessions WHERE party_id=? ORDER BY created_at DESC',(pid,)) if uid in json.loads(row['participants_json']) and not conn.execute('SELECT 1 FROM provider_staff WHERE provider_id=? AND user_id=?',(row['provider_id'],uid)).fetchone()]
            return dict(items=items,reflections=reflections)

    def list(self,uid,pid):
        return {'items':self.options(uid,pid)['reflections']}

    def get(self,uid,rid):
        with self.db.transaction() as conn:
            return self.detail(conn,uid,self.access(conn,uid,rid))

    def create(self,uid,pid,data):
        with self.db.transaction(True) as conn:
            invitation=require(conn.execute('SELECT * FROM circle_provider_invitations WHERE id=? AND party_id=? AND accepted_at IS NOT NULL',(data['invitation_id'],pid)).fetchone())
            self.traveler(conn,uid,pid,invitation['provider_id'],True)
            operation='reflection:create:'+pid
            previous,fingerprint=self.market.replay(conn,uid,operation,data)
            if previous:
                return self.detail(conn,uid,self.access(conn,uid,previous))
            existing=conn.execute('SELECT * FROM reflection_sessions WHERE party_id=? AND provider_id=?',(pid,invitation['provider_id'])).fetchone()
            if existing:
                raise HTTPException(409,'この講と事業者の振り返りは作成済みです。')
            if data['ended_on']<self.earliest(invitation):
                raise HTTPException(422,'参加依頼の受諾日・共有した出発日以後の終了日を確認してください。')
            rid=identifier()
            targets=current_participants(conn,dict(party_id=pid,provider_id=invitation['provider_id']))
            if uid not in targets:
                raise HTTPException(404,'対象の旅行者を確認できません。')
            conn.execute('INSERT INTO reflection_sessions(id,party_id,provider_id,invitation_id,ended_on,trip_finished,participants_json,created_at) VALUES(?,?,?,?,?,1,?,?)',(rid,pid,invitation['provider_id'],invitation['id'],data['ended_on'],dump(targets),now()))
            conn.executemany('INSERT INTO reflection_participants(reflection_id,epoch,user_id,updated_at) VALUES(?,1,?,?)',[(rid,person,now()) for person in targets])
            self.market.remember(conn,uid,operation,data,fingerprint,rid)
            return self.detail(conn,uid,self.access(conn,uid,rid))

    @staticmethod
    def analyze_pending(conn,reflection):
        if not state(conn,reflection)['ready_for_analysis']:
            return
        provider=conn.execute('SELECT name FROM providers WHERE id=?',(reflection['provider_id'],)).fetchone()[0]
        for message in conn.execute('SELECT id,body FROM reflection_messages WHERE reflection_id=? AND epoch=? AND deleted=0 AND auto_json IS NULL',(reflection['id'],reflection['epoch'])).fetchall():
            conn.execute('UPDATE reflection_messages SET auto_json=? WHERE id=?',(dump(extract(message['body'],provider)),message['id']))

    def participant(self,uid,rid,data,consent=False):
        with self.db.transaction(True) as conn:
            row=self.access(conn,uid,rid)
            status=state(conn,row)
            if (data['allowed'] if consent else data['used_service']) and not status['participant_set_current']:
                raise HTTPException(409,'対象者が変わりました。代表者による対象者の更新を確認してください。')
            own=require(conn.execute('SELECT * FROM reflection_participants WHERE reflection_id=? AND epoch=? AND user_id=?',(rid,row['epoch'],uid)).fetchone())
            if own['version']!=data['version']:
                conflict()
            if consent:
                if data['allowed'] and not own['used_service']:
                    raise HTTPException(409,'実際に利用したことを先に確認してください。')
                conn.execute('UPDATE reflection_participants SET consented=?,version=version+1,updated_at=? WHERE reflection_id=? AND epoch=? AND user_id=?',(int(data['allowed']),now(),rid,row['epoch'],uid))
            else:
                conn.execute('UPDATE reflection_participants SET used_service=?,consented=CASE WHEN ?=0 THEN 0 ELSE consented END,version=version+1,updated_at=? WHERE reflection_id=? AND epoch=? AND user_id=?',(int(data['used_service']),int(data['used_service']),now(),rid,row['epoch'],uid))
            self.analyze_pending(conn,row)
            return self.detail(conn,uid,row)

    @staticmethod
    def reset_participants(conn,row):
        targets=current_participants(conn,row)
        epoch=row['epoch']+1
        conn.execute('UPDATE reflection_sessions SET participants_json=?,participants_valid=1,epoch=?,version=version+1 WHERE id=?',(dump(targets),epoch,row['id']))
        conn.executemany('INSERT INTO reflection_participants(reflection_id,epoch,user_id,updated_at) VALUES(?,?,?,?)',[(row['id'],epoch,person,now()) for person in targets])

    def refresh(self,uid,rid,version):
        with self.db.transaction(True) as conn:
            row=self.access(conn,uid,rid,True)
            if row['version']!=version:
                conflict()
            if state(conn,row)['participant_set_current']:
                raise HTTPException(409,'対象者は変わっていません。')
            self.reset_participants(conn,row)
            return self.detail(conn,uid,self.access(conn,uid,rid))

    def completion(self,uid,rid,data):
        with self.db.transaction(True) as conn:
            row=self.access(conn,uid,rid,True)
            if row['version']!=data['version']:
                conflict()
            if bool(row['trip_finished'])==data['trip_finished']:
                return self.detail(conn,uid,row)
            if data['trip_finished']:
                self.reset_participants(conn,row)
            conn.execute('UPDATE reflection_sessions SET trip_finished=?,version=version+1 WHERE id=?',(int(data['trip_finished']),rid))
            return self.detail(conn,uid,self.access(conn,uid,rid))

    def post(self,uid,rid,data):
        with self.db.transaction(True) as conn:
            row=self.access(conn,uid,rid)
            if not state(conn,row)['participant_set_current'] or not row['trip_finished']:
                raise HTTPException(409,'旅行終了と現在の対象者を確認してから振り返りを投稿してください。')
            operation='reflection:message:'+rid+':'+str(row['epoch'])
            previous,fingerprint=self.market.replay(conn,uid,operation,data)
            if previous:
                message=require(conn.execute('SELECT * FROM reflection_messages WHERE id=? AND deleted=0',(previous,)).fetchone())
                return self.message_out(conn,message,uid,row)
            if conn.execute('SELECT COUNT(*) FROM reflection_messages WHERE reflection_id=? AND epoch=?',(rid,row['epoch'])).fetchone()[0]>=100:
                raise HTTPException(409,'この振り返り区間の発言は100件までです。')
            mid,at=identifier(),now()
            conn.execute('INSERT INTO reflection_messages(id,reflection_id,epoch,author_id,body,created_at,updated_at) VALUES(?,?,?,?,?,?,?)',(mid,rid,row['epoch'],uid,data['body'],at,at))
            self.analyze_pending(conn,row)
            self.market.remember(conn,uid,operation,data,fingerprint,mid)
            return self.message_out(conn,conn.execute('SELECT * FROM reflection_messages WHERE id=?',(mid,)).fetchone(),uid,row)

    def edit(self,uid,mid,data,delete=False,review=False):
        with self.db.transaction(True) as conn:
            message=require(conn.execute('SELECT * FROM reflection_messages WHERE id=? AND author_id=? AND deleted=0',(mid,uid)).fetchone())
            reflection=self.access(conn,uid,message['reflection_id'])
            if message['epoch']!=reflection['epoch'] or message['version']!=data['version']:
                conflict()
            if delete:
                conn.execute("UPDATE reflection_messages SET body='',deleted=1,auto_json=NULL,override_json=NULL,override_source_version=NULL,source_version=source_version+1,version=version+1,updated_at=? WHERE id=?",(now(),mid))
                return {'ok':True}
            if review:
                _,automatic=effective(message)
                if not state(conn,reflection)['ready_for_analysis'] or not automatic or not automatic['eligible']:
                    raise HTTPException(409,'この発言は参考集計の対象外です。対象事業者の体験として書き直してください。')
                if data['source_version']!=message['source_version']:
                    conflict()
                conn.execute('UPDATE reflection_messages SET override_json=?,override_source_version=?,version=version+1,updated_at=? WHERE id=?',(dump(data['values']),message['source_version'],now(),mid))
            else:
                conn.execute('UPDATE reflection_messages SET body=?,source_version=source_version+1,version=version+1,auto_json=NULL,override_json=NULL,override_source_version=NULL,updated_at=? WHERE id=?',(data['body'],now(),mid))
                self.analyze_pending(conn,reflection)
            return self.message_out(conn,conn.execute('SELECT * FROM reflection_messages WHERE id=?',(mid,)).fetchone(),uid,reflection)

    def public(self,provider_id):
        with self.db.transaction() as conn:
            require(conn.execute('SELECT 1 FROM providers WHERE id=? AND active=1',(provider_id,)).fetchone())
            return public_summary(conn,provider_id)
