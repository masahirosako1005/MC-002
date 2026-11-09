import json

from fastapi import HTTPException
from ..database import identifier, now
from ..marketplace.service import conflict, dump
from ..service import require, user_out
from .guards import require_active_shared_room


class ProviderMixin:
    @staticmethod
    def provider_invitation_out(conn, row):
        return dict(id=row['id'],circle_id=row['party_id'],provider=dict(conn.execute('SELECT id,name,area FROM providers WHERE id=?',(row['provider_id'],)).fetchone()),
                    inviter_name=conn.execute('SELECT name FROM users WHERE id=?',(row['inviter_id'],)).fetchone()[0],
                    status=row['status'],version=row['version'],snapshot=json.loads(row['snapshot']),
                    consultation_id=row['consultation_id'],created_at=row['created_at'],accepted_at=row['accepted_at'])

    def invite_provider(self, uid, pid, data):
        with self.db.transaction(True) as conn:
            self.party(conn,uid,pid,True)
            operation = 'circle:provider-invite:'+pid
            previous,fingerprint = self.market.replay(conn,uid,operation,data)
            if previous:
                return self.provider_invitation_out(conn,require(conn.execute('SELECT * FROM circle_provider_invitations WHERE id=?',(previous,)).fetchone()))
            self.version(conn,pid,data['version'])
            if conn.execute("SELECT 1 FROM circle_provider_invitations WHERE party_id=? AND status IN ('pending','accepted')",(pid,)).fetchone():
                raise HTTPException(409,'参加依頼中の事業者がいます。現在の依頼を閉じてから選び直してください。')
            if conn.execute('SELECT COUNT(*) FROM circle_provider_invitations WHERE party_id=?',(pid,)).fetchone()[0] >= 100:
                raise HTTPException(409,'この講の事業者への依頼は100件までです。')
            preview = self.market.preview(conn,uid,pid,data)
            snapshot = dict(plan=preview['plan'],shared_conditions=preview['shared_conditions'],share_note=data['share_note'],
                            requirements_version=data['requirements_version'],unknowns=preview['match']['unknowns'])
            iid = identifier()
            conn.execute("INSERT INTO circle_provider_invitations VALUES(?,?,?,?,?,'pending',1,NULL,?,NULL)",
                         (iid,pid,preview['plan']['provider']['id'],uid,dump(snapshot),now()))
            self.market.remember(conn,uid,operation,data,fingerprint,iid)
            return self.provider_invitation_out(conn,conn.execute('SELECT * FROM circle_provider_invitations WHERE id=?',(iid,)).fetchone())

    def provider_invitations(self, uid):
        with self.db.transaction() as conn:
            rows = conn.execute("SELECT i.* FROM circle_provider_invitations i JOIN provider_staff s ON s.provider_id=i.provider_id AND s.user_id=? AND s.active=1 JOIN providers p ON p.id=i.provider_id AND p.active=1 WHERE i.status IN ('pending','accepted') ORDER BY i.created_at DESC LIMIT 100",(uid,))
            return {'items':[self.provider_invitation_out(conn,row) for row in rows]}

    def provider_response(self, uid, iid, data, cancel=False):
        with self.db.transaction(True) as conn:
            row = require(conn.execute('SELECT * FROM circle_provider_invitations WHERE id=?',(iid,)).fetchone())
            if cancel:
                self.party(conn,uid,row['party_id'],True)
            else:
                self.market.staff(conn,uid,row['provider_id'])
                require(conn.execute("SELECT 1 FROM travel_parties WHERE id=? AND status='open'",(row['party_id'],)).fetchone())
            operation = ('circle:provider-cancel:' if cancel else 'circle:provider-respond:')+iid
            previous,fingerprint = self.market.replay(conn,uid,operation,data)
            if previous:
                return self.provider_invitation_out(conn,row)
            if row['version'] != data['version'] or row['status'] not in (('pending','accepted') if cancel else ('pending',)):
                conflict()
            status = 'cancelled' if cancel else data['decision']
            cid, accepted_at = row['consultation_id'],row['accepted_at']
            if status == 'accepted':
                snapshot = json.loads(row['snapshot'])
                # Revalidate both authority and the exact shared revision; stale consent is not reused.
                self.market.preview(conn,row['inviter_id'],row['party_id'],dict(plan_id=snapshot['plan']['id'],
                    plan_version=snapshot['plan']['version'],requirements_version=snapshot['requirements_version']))
                conn.execute("UPDATE consultations SET status='closed',version=version+1 WHERE selection_id IN (SELECT id FROM plan_selections WHERE party_id=? AND status='active')",(row['party_id'],))
                conn.execute("UPDATE plan_selections SET status='closed' WHERE party_id=? AND status='active'",(row['party_id'],))
                sid,cid,accepted_at = identifier(),identifier(),now()
                conn.execute("INSERT INTO plan_selections VALUES(?,?,?,?,?,?,'active',?)",(sid,row['party_id'],snapshot['plan']['id'],row['provider_id'],row['snapshot'],row['inviter_id'],accepted_at))
                conn.execute("INSERT INTO consultations(id,selection_id,status,created_at) VALUES(?,?,'open',?)",(cid,sid,accepted_at))
            conn.execute('UPDATE circle_provider_invitations SET status=?,version=version+1,consultation_id=?,accepted_at=? WHERE id=?',(status,cid,accepted_at,iid))
            self.market.remember(conn,uid,operation,data,fingerprint,iid)
            return self.provider_invitation_out(conn,conn.execute('SELECT * FROM circle_provider_invitations WHERE id=?',(iid,)).fetchone())

    def shared_access(self, conn, uid, iid):
        row = require(conn.execute("SELECT * FROM circle_provider_invitations WHERE id=? AND status='accepted'",(iid,)).fetchone())
        require_active_shared_room(conn,row['consultation_id'])
        staff = conn.execute('SELECT 1 FROM provider_staff s JOIN providers p ON p.id=s.provider_id WHERE s.user_id=? AND s.provider_id=? AND s.active=1 AND p.active=1',(uid,row['provider_id'])).fetchone()
        if staff:
            role,can_confirm = 'provider',True
        else:
            party = self.party(conn,uid,row['party_id'],open_only=True)
            role,can_confirm = 'traveler',party['representative_id'] == uid
        return row,role,can_confirm

    @staticmethod
    def proposal_out(conn, row):
        confirmations = [dict(role=confirmation['role'],user=user_out(conn.execute('SELECT * FROM users WHERE id=?',(confirmation['user_id'],)).fetchone()),confirmed_at=confirmation['confirmed_at'])
                         for confirmation in conn.execute('SELECT * FROM circle_confirmations WHERE proposal_id=? ORDER BY role',(row['id'],))]
        return dict(**json.loads(row['body']),id=row['id'],invitation_id=row['invitation_id'],version=row['version'],
                    created_at=row['created_at'],created_by=row['created_by'],confirmations=confirmations,
                    status='both_confirmed' if {item['role'] for item in confirmations} == {'traveler','provider'} else 'awaiting_confirmation',reservation_status='not_booked')

    def shared_room(self, uid, iid):
        with self.db.transaction() as conn:
            row,role,can_confirm = self.shared_access(conn,uid,iid)
            messages = conn.execute('SELECT * FROM consultation_messages WHERE consultation_id=? ORDER BY created_at DESC,id DESC LIMIT 100',(row['consultation_id'],)).fetchall()
            proposal = conn.execute('SELECT * FROM circle_proposals WHERE invitation_id=? ORDER BY version DESC LIMIT 1',(iid,)).fetchone()
            return dict(invitation=self.provider_invitation_out(conn,row),messages=[self.market.message_out(conn,message) for message in reversed(messages)],
                        proposal=self.proposal_out(conn,proposal) if proposal else None,can_propose=role=='provider',can_confirm=can_confirm,my_role=role,reservation_status='not_booked')

    def shared_message(self, uid, iid, data):
        with self.db.transaction(True) as conn:
            row,_,_ = self.shared_access(conn,uid,iid)
            operation = 'circle:shared-message:'+iid
            previous,fingerprint = self.market.replay(conn,uid,operation,data)
            if previous:
                return self.market.message_out(conn,require(conn.execute('SELECT * FROM consultation_messages WHERE id=? AND consultation_id=?',(previous,row['consultation_id'])).fetchone()))
            mid = identifier()
            conn.execute('INSERT INTO consultation_messages VALUES(?,?,?,?,?)',(mid,row['consultation_id'],uid,data['body'],now()))
            self.market.remember(conn,uid,operation,data,fingerprint,mid)
            return self.market.message_out(conn,conn.execute('SELECT * FROM consultation_messages WHERE id=?',(mid,)).fetchone())

    def propose_agreement(self, uid, iid, data):
        with self.db.transaction(True) as conn:
            row,role,_ = self.shared_access(conn,uid,iid)
            if role != 'provider':
                raise HTTPException(404,'行程・見積を提出できる事業者ではありません。')
            operation = 'circle:proposal:'+iid
            previous,fingerprint = self.market.replay(conn,uid,operation,data)
            if previous:
                return self.proposal_out(conn,require(conn.execute('SELECT * FROM circle_proposals WHERE id=? AND invitation_id=?',(previous,iid)).fetchone()))
            current = conn.execute('SELECT MAX(version) FROM circle_proposals WHERE invitation_id=?',(iid,)).fetchone()[0] or 0
            if data['version'] != current:
                conflict()
            if current >= 100:
                raise HTTPException(409,'行程・見積の改訂は100版までです。')
            snapshot = json.loads(row['snapshot'])
            if {item['day'] for item in data['itinerary']} != set(range(1,snapshot['shared_conditions']['nights']+2)):
                raise HTTPException(422,'共有した泊数に合わせて、すべての日の行程を入れてください。')
            pid = identifier()
            body = {key:value for key,value in data.items() if key not in ('version','client_request_id')}
            conn.execute('INSERT INTO circle_proposals VALUES(?,?,?,?,?,?)',(pid,iid,current+1,dump(body),uid,now()))
            self.market.remember(conn,uid,operation,data,fingerprint,pid)
            return self.proposal_out(conn,conn.execute('SELECT * FROM circle_proposals WHERE id=?',(pid,)).fetchone())

    def confirm_agreement(self, uid, iid, data):
        with self.db.transaction(True) as conn:
            _,role,can_confirm = self.shared_access(conn,uid,iid)
            if not can_confirm:
                raise HTTPException(404,'行程・見積は旅行者の代表が確認してください。')
            proposal = require(conn.execute('SELECT * FROM circle_proposals WHERE id=? AND invitation_id=?',(data['proposal_id'],iid)).fetchone())
            latest = conn.execute('SELECT MAX(version) FROM circle_proposals WHERE invitation_id=?',(iid,)).fetchone()[0]
            # Check current revision before replay: an old confirmation cannot endorse a newer offer.
            if proposal['version'] != data['version'] or latest != data['version']:
                conflict()
            operation = 'circle:confirm:'+iid
            previous,fingerprint = self.market.replay(conn,uid,operation,data)
            if not previous:
                conn.execute('INSERT OR IGNORE INTO circle_confirmations VALUES(?,?,?,?)',(proposal['id'],role,uid,now()))
                self.market.remember(conn,uid,operation,data,fingerprint,proposal['id'])
            return self.proposal_out(conn,proposal)
