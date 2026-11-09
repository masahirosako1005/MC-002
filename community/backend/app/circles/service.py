import json

from fastapi import HTTPException

from ..database import identifier, now
from ..marketplace.service import Marketplace, conflict, dump
from ..service import member, require, user_out
from .assistant import AssistantMixin
from .providers import ProviderMixin


class Circles(AssistantMixin, ProviderMixin):
    def __init__(self, database):
        self.db = database
        self.market = Marketplace(database)

    def party(self, conn, uid, pid, representative=False, open_only=False):
        row = self.market.party(conn, uid, pid, representative)
        if open_only and row['status'] != 'open':
            raise HTTPException(409, 'この講の計画は閉じています。')
        return row

    @staticmethod
    def room(conn, pid, create=False):
        row = conn.execute('SELECT * FROM circle_rooms WHERE party_id=?', (pid,)).fetchone()
        if row is None:
            count = conn.execute('SELECT COUNT(*) FROM travel_party_members WHERE party_id=?', (pid,)).fetchone()[0]
            if create:
                conn.execute("INSERT INTO circle_rooms VALUES(?,'legacy',?,'[]',1,?)", (pid,max(2,count),now()))
                row = conn.execute('SELECT * FROM circle_rooms WHERE party_id=?', (pid,)).fetchone()
            else:
                row = dict(party_id=pid,mode='legacy',desired_count=max(2,count),tags='[]',version=1)
        return row

    def version(self, conn, pid, version):
        row = self.room(conn,pid,True)
        if row['version'] != version:
            conflict()

    @staticmethod
    def invitation_out(conn, row):
        party = require(conn.execute('SELECT title FROM travel_parties WHERE id=?',(row['party_id'],)).fetchone())
        return dict(id=row['id'],circle_id=row['party_id'],circle_title=party['title'],
                    invitee=user_out(conn.execute('SELECT * FROM users WHERE id=?',(row['invitee_id'],)).fetchone()),
                    inviter=user_out(conn.execute('SELECT * FROM users WHERE id=?',(row['inviter_id'],)).fetchone()),
                    status=row['status'],version=row['version'],created_at=row['created_at'])

    def circle_out(self, conn, uid, party, detail=False):
        room = self.room(conn,party['id'])
        result = self.market.party_out(conn,uid,party)
        invited = conn.execute("SELECT * FROM circle_member_invitations WHERE party_id=? AND status='pending' ORDER BY created_at,id",(party['id'],)).fetchall()
        shared = conn.execute("SELECT * FROM circle_provider_invitations WHERE party_id=? AND status IN ('pending','accepted')",(party['id'],)).fetchone()
        count = result['active_account_count']
        result.update(version=room['version'],mode=room['mode'],tags=json.loads(room['tags']),desired_count=room['desired_count'],accepted_count=count,
                      pending_count=len(invited),shortage_count=max(0,room['desired_count']-count-len(invited)),
                      active_provider_invitation=self.provider_invitation_out(conn,shared) if shared else None)
        if detail:
            result['members'] = [user_out(row) for row in conn.execute("SELECT u.* FROM users u JOIN travel_party_members pm ON pm.user_id=u.id JOIN memberships m ON m.user_id=u.id AND m.community_id=? WHERE pm.party_id=? AND m.status='active' AND u.login_enabled=1 ORDER BY u.id",(party['community_id'],party['id']))]
            result['invitations'] = [self.invitation_out(conn,row) for row in invited]
        return result

    def candidates_in(self, conn, uid, data):
        member(conn,uid,data['community_id'])
        rows = conn.execute("""SELECT u.*,p.tags FROM users u
            JOIN memberships m ON m.user_id=u.id AND m.community_id=? AND m.status='active'
            JOIN grants g ON g.user_id=u.id AND g.community_id=m.community_id
            JOIN preferences p ON p.user_id=u.id
            WHERE u.login_enabled=1 AND u.id!=? AND g.use_matching=1 AND g.display_matching=1 AND g.participate=1 ORDER BY u.id""",(data['community_id'],uid)).fetchall()
        items = [dict(user=user_out(row),common_tags=sorted(set(data['tags']) & set(json.loads(row['tags'])))) for row in rows]
        items = [item for item in items if item['common_tags']]
        items.sort(key=lambda item:(-len(item['common_tags']),item['user']['id']))
        return dict(items=items[:100],desired_count=data['desired_count'],available_count=len(items)+1,
                    shortage_count=max(0,data['desired_count']-len(items)-1),method='consented-interest-match-v1')

    def candidates(self, uid, data):
        with self.db.transaction() as conn:
            return self.candidates_in(conn,uid,data)

    def create(self, uid, data):
        with self.db.transaction(True) as conn:
            member(conn,uid,data['community_id'])
            previous,fingerprint = self.market.replay(conn,uid,'circle:create',data)
            if previous:
                return self.circle_out(conn,uid,self.party(conn,uid,previous),True)
            if conn.execute('SELECT COUNT(*) FROM travel_parties WHERE representative_id=?',(uid,)).fetchone()[0] >= 100:
                raise HTTPException(409,'代表として作成できる講は100件までです。')
            if uid in data['invitee_ids']:
                raise HTTPException(422,'自分への招待は必要ありません。')
            if data['mode'] == 'recommended':
                eligible = {item['user']['id'] for item in self.candidates_in(conn,uid,data)['items']}
                if not set(data['invitee_ids']) <= eligible:
                    raise HTTPException(409,'候補の関心や許可が変わりました。候補を開き直してください。')
            pid = identifier()
            conn.execute("INSERT INTO travel_parties VALUES(?,?,NULL,?,?,'open',?)",(pid,data['community_id'],uid,data['title'],now()))
            conn.execute('INSERT INTO travel_party_members VALUES(?,?)',(pid,uid))
            conn.execute('INSERT INTO circle_rooms VALUES(?,?,?,?,1,?)',(pid,data['mode'],data['desired_count'],dump(data['tags']),now()))
            self.add_invitations(conn,uid,self.party(conn,uid,pid),data['invitee_ids'])
            self.market.remember(conn,uid,'circle:create',data,fingerprint,pid)
            return self.circle_out(conn,uid,self.party(conn,uid,pid),True)

    def add_invitations(self, conn, uid, party, people):
        pid = party['id']
        room = self.room(conn,pid,True)
        total = conn.execute('SELECT COUNT(*) FROM circle_member_invitations WHERE party_id=?',(pid,)).fetchone()[0]
        if total + len(people) > 100:
            raise HTTPException(409,'この講の招待履歴は100件までです。')
        pending = conn.execute("SELECT COUNT(*) FROM circle_member_invitations WHERE party_id=? AND status='pending'",(pid,)).fetchone()[0]
        joined = conn.execute('SELECT COUNT(*) FROM travel_party_members WHERE party_id=?',(pid,)).fetchone()[0]
        if pending + joined + len(people) > room['desired_count']:
            raise HTTPException(409,'希望人数を超えています。招待中の人を確認してください。')
        for person in people:
            member(conn,person,party['community_id'])
            require(conn.execute('SELECT 1 FROM users WHERE id=? AND login_enabled=1',(person,)).fetchone())
            if conn.execute('SELECT 1 FROM travel_party_members WHERE party_id=? AND user_id=?',(pid,person)).fetchone() or conn.execute("SELECT 1 FROM circle_member_invitations WHERE party_id=? AND invitee_id=? AND status='pending'",(pid,person)).fetchone():
                raise HTTPException(409,'参加済み、または招待中の人が含まれています。')
            # Existing legacy groups have a separate explicit-consent membership boundary.
            if party['ko_group_id']:
                require(conn.execute('SELECT 1 FROM group_members WHERE group_id=? AND user_id=?',(party['ko_group_id'],person)).fetchone())
            conn.execute("INSERT INTO circle_member_invitations VALUES(?,?,?,?,'pending',1,?)",(identifier(),pid,person,uid,now()))

    def invite(self, uid, pid, data):
        with self.db.transaction(True) as conn:
            party = self.party(conn,uid,pid,True)
            operation = 'circle:invite:'+pid
            previous,fingerprint = self.market.replay(conn,uid,operation,data)
            if previous:
                return self.circle_out(conn,uid,party,True)
            self.version(conn,pid,data['version'])
            self.add_invitations(conn,uid,party,data['invitee_ids'])
            self.market.remember(conn,uid,operation,data,fingerprint,pid)
            return self.circle_out(conn,uid,party,True)

    def respond(self, uid, iid, data, cancel=False):
        with self.db.transaction(True) as conn:
            row = require(conn.execute('SELECT * FROM circle_member_invitations WHERE id=?',(iid,)).fetchone())
            if cancel:
                self.party(conn,uid,row['party_id'],True)
            else:
                if uid != row['invitee_id']:
                    raise HTTPException(404,'招待が見つかりません。')
                party = require(conn.execute("SELECT * FROM travel_parties WHERE id=? AND status='open'",(row['party_id'],)).fetchone())
                member(conn,uid,party['community_id'])
                member(conn,party['representative_id'],party['community_id'])
            operation = 'circle:cancel:' + iid if cancel else 'circle:respond:' + iid
            previous,fingerprint = self.market.replay(conn,uid,operation,data)
            if previous:
                return self.invitation_out(conn,row)
            if row['version'] != data['version'] or row['status'] != 'pending':
                conflict()
            status = 'cancelled' if cancel else data['decision']
            if status == 'accepted':
                conn.execute('INSERT INTO travel_party_members VALUES(?,?)',(row['party_id'],uid))
            conn.execute('UPDATE circle_member_invitations SET status=?,version=version+1 WHERE id=?',(status,iid))
            self.market.remember(conn,uid,operation,data,fingerprint,iid)
            return self.invitation_out(conn,conn.execute('SELECT * FROM circle_member_invitations WHERE id=?',(iid,)).fetchone())

    def list(self, uid):
        with self.db.transaction() as conn:
            items = []
            for row in conn.execute("SELECT p.* FROM travel_parties p JOIN travel_party_members pm ON pm.party_id=p.id JOIN memberships m ON m.user_id=pm.user_id AND m.community_id=p.community_id AND m.status='active' WHERE pm.user_id=? ORDER BY p.created_at DESC LIMIT 100",(uid,)):
                try:
                    self.party(conn,uid,row['id'])
                    items.append(self.circle_out(conn,uid,row))
                except HTTPException as exc:
                    if exc.status_code != 404:
                        raise
            invitations = [self.invitation_out(conn,row) for row in conn.execute("SELECT i.* FROM circle_member_invitations i JOIN travel_parties p ON p.id=i.party_id JOIN memberships m ON m.community_id=p.community_id AND m.user_id=i.invitee_id AND m.status='active' WHERE i.invitee_id=? AND i.status='pending' AND p.status='open' ORDER BY i.created_at DESC LIMIT 100",(uid,))]
            groups = [dict(id=row['id'],purpose=row['purpose'],community_id=row['community_id'],member_count=conn.execute("SELECT COUNT(*) FROM group_members gm JOIN memberships m ON m.user_id=gm.user_id AND m.community_id=? AND m.status='active' WHERE gm.group_id=?",(row['community_id'],row['id'])).fetchone()[0],
                           circle_id=(found[0] if (found:=conn.execute('SELECT p.id FROM travel_parties p JOIN travel_party_members pm ON pm.party_id=p.id AND pm.user_id=? WHERE p.ko_group_id=? ORDER BY p.created_at LIMIT 1',(uid,row['id'])).fetchone()) else None))
                      for row in conn.execute("SELECT g.* FROM ko_groups g JOIN group_members gm ON gm.group_id=g.id JOIN memberships m ON m.user_id=gm.user_id AND m.community_id=g.community_id WHERE gm.user_id=? AND m.status='active' ORDER BY g.created_at DESC LIMIT 100",(uid,))]
            return dict(items=items,invitations=invitations,groups=groups)

    def get(self, uid, pid):
        with self.db.transaction() as conn:
            return self.circle_out(conn,uid,self.party(conn,uid,pid),True)

    def preferences(self,uid,pid,data):
        with self.db.transaction(True) as conn:
            party=self.party(conn,uid,pid,True)
            self.version(conn,pid,data['version'])
            conn.execute('UPDATE circle_rooms SET tags=?,version=version+1 WHERE party_id=?',(dump(data['tags']),pid))
            return self.circle_out(conn,uid,party,True)

    def from_group(self, uid, data):
        with self.db.transaction(True) as conn:
            group = require(conn.execute('SELECT g.* FROM ko_groups g JOIN group_members m ON m.group_id=g.id WHERE g.id=? AND m.user_id=?',(data['group_id'],uid)).fetchone())
            member(conn,uid,group['community_id'])
            previous,fingerprint = self.market.replay(conn,uid,'circle:from-group',data)
            if previous:
                return self.circle_out(conn,uid,self.party(conn,uid,previous),True)
            existing = conn.execute('SELECT p.id FROM travel_parties p JOIN travel_party_members pm ON pm.party_id=p.id AND pm.user_id=? WHERE p.ko_group_id=? ORDER BY p.created_at LIMIT 1',(uid,group['id'])).fetchone()
            if existing:
                pid = existing['id']
                self.party(conn,uid,pid)
            else:
                if conn.execute('SELECT COUNT(*) FROM travel_parties WHERE representative_id=?',(uid,)).fetchone()[0] >= 100:
                    raise HTTPException(409,'代表として作成できる講は100件までです。')
                people = [row[0] for row in conn.execute("SELECT gm.user_id FROM group_members gm JOIN memberships m ON m.user_id=gm.user_id AND m.community_id=? JOIN users u ON u.id=gm.user_id WHERE gm.group_id=? AND m.status='active' AND u.login_enabled=1",(group['community_id'],group['id']))]
                pid = identifier()
                conn.execute("INSERT INTO travel_parties VALUES(?,?,?,?,?,'open',?)",(pid,group['community_id'],group['id'],uid,group['purpose'],now()))
                conn.executemany('INSERT INTO travel_party_members VALUES(?,?)',[(pid,person) for person in people])
                conn.execute("INSERT INTO circle_rooms VALUES(?,'existing-group',?,'[]',1,?)",(pid,max(2,len(people)),now()))
            self.market.remember(conn,uid,'circle:from-group',data,fingerprint,pid)
            return self.circle_out(conn,uid,self.party(conn,uid,pid),True)

    def leave(self, uid, pid, version):
        with self.db.transaction(True) as conn:
            party = self.party(conn,uid,pid,open_only=True)
            if party['representative_id'] == uid:
                raise HTTPException(409,'代表者は講の計画を閉じてください。')
            self.version(conn,pid,version)
            conn.execute('DELETE FROM travel_party_members WHERE party_id=? AND user_id=?',(pid,uid))
            conn.execute("UPDATE circle_member_invitations SET status='left',version=version+1 WHERE party_id=? AND invitee_id=? AND status='accepted'",(pid,uid))
            return {'ok':True}

    def close(self, uid, pid, version):
        with self.db.transaction(True) as conn:
            self.party(conn,uid,pid,True)
            self.version(conn,pid,version)
            conn.execute("UPDATE travel_parties SET status='closed' WHERE id=?",(pid,))
            conn.execute("UPDATE consultations SET status='closed',version=version+1 WHERE selection_id IN (SELECT id FROM plan_selections WHERE party_id=? AND status='active')",(pid,))
            conn.execute("UPDATE plan_selections SET status='closed' WHERE party_id=? AND status='active'",(pid,))
            return self.circle_out(conn,uid,conn.execute('SELECT * FROM travel_parties WHERE id=?',(pid,)).fetchone(),True)
