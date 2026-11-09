import heapq
import json

from fastapi import HTTPException

from ..circles.discovery import Discovery
from ..database import digest, identifier, now
from ..marketplace.schedules import schedule_match
from ..marketplace.service import Marketplace, conflict, dump
from ..reflections.aggregate import public_summary
from ..service import require, user_out
from .access import permitted_share
from .dates import next_occurrence


class Occasions:
    def __init__(self,database):
        self.db=database
        self.market=Marketplace(database)
        self.discovery=Discovery(database)

    def party(self,conn,uid,pid):
        party=self.market.party(conn,uid,pid)
        if party['status']!='open':
            raise HTTPException(404,'参加中の講を選んでください。')
        return party

    @staticmethod
    def own(conn,uid,oid):
        return require(conn.execute('SELECT * FROM occasions WHERE id=? AND user_id=? AND deleted=0',(oid,uid)).fetchone())

    @staticmethod
    def occurrence(row):
        return next_occurrence(row['month'],row['day'],repeats_annually=bool(row['repeats_annually']),year=row['year'])

    def circles(self,conn,uid):
        items=[]
        for row in conn.execute("SELECT p.id,p.title,p.community_id FROM travel_parties p JOIN travel_party_members pm ON pm.party_id=p.id JOIN memberships m ON m.community_id=p.community_id AND m.user_id=pm.user_id WHERE pm.user_id=? AND m.status='active' AND p.status='open' ORDER BY p.created_at DESC,p.id LIMIT 100",(uid,)):
            try:
                self.party(conn,uid,row['id'])
            except HTTPException:
                continue
            items.append(dict(row))
        return items

    def out(self,conn,row):
        allowed={p['id']:p for p in self.circles(conn,row['user_id'])}
        sharing=[dict(circle_id=s['party_id'],circle_title=allowed[s['party_id']]['title'],share_date=bool(s['share_date']),suggest=bool(s['suggest'])) for s in conn.execute('SELECT * FROM occasion_sharing WHERE occasion_id=? ORDER BY party_id',(row['id'],)) if s['party_id'] in allowed]
        return dict(id=row['id'],kind=row['kind'],name=row['name'],month=row['month'],day=row['day'],repeats_annually=bool(row['repeats_annually']),year=row['year'],version=row['version'],sharing=sharing,next_occurrence=self.occurrence(row))

    def list(self,uid):
        with self.db.transaction() as conn:
            return dict(items=[self.out(conn,row) for row in conn.execute('SELECT * FROM occasions WHERE user_id=? AND deleted=0 ORDER BY created_at,id',(uid,))],circles=self.circles(conn,uid))

    def create(self,uid,data):
        with self.db.transaction(True) as conn:
            previous,fingerprint=self.market.replay(conn,uid,'occasion:create',data)
            if previous:
                return self.out(conn,self.own(conn,uid,previous))
            self.validate_limit(conn,uid,data['kind'])
            oid=identifier()
            conn.execute('INSERT INTO occasions(id,user_id,kind,name,month,day,repeats_annually,year,created_at) VALUES(?,?,?,?,?,?,?,?,?)',(oid,uid,data['kind'],data['name'],data['month'],data['day'],int(data['repeats_annually']),data['year'],now()))
            self.market.remember(conn,uid,'occasion:create',data,fingerprint,oid)
            return self.out(conn,self.own(conn,uid,oid))

    @staticmethod
    def validate_limit(conn,uid,kind,except_id=None):
        if kind=='birthday' and conn.execute("SELECT 1 FROM occasions WHERE user_id=? AND kind='birthday' AND deleted=0 AND id!=?",(uid,except_id or '')).fetchone():
            raise HTTPException(409,'誕生日は登録済みです。登録した内容を編集してください。')
        if not except_id and conn.execute('SELECT COUNT(*) FROM occasions WHERE user_id=? AND deleted=0',(uid,)).fetchone()[0]>=20:
            raise HTTPException(409,'登録できる誕生日・記念日は20件までです。')

    def edit(self,uid,oid,data,delete=False):
        with self.db.transaction(True) as conn:
            row=self.own(conn,uid,oid)
            if row['version']!=data['version']:
                conflict()
            if delete:
                conn.execute('UPDATE occasions SET deleted=1,version=version+1 WHERE id=?',(oid,))
                conn.execute('UPDATE occasion_sharing SET share_date=0,suggest=0,version=version+1 WHERE occasion_id=?',(oid,))
                return {'ok':True}
            self.validate_limit(conn,uid,data['kind'],oid)
            conn.execute('UPDATE occasions SET kind=?,name=?,month=?,day=?,repeats_annually=?,year=?,version=version+1 WHERE id=?',(data['kind'],data['name'],data['month'],data['day'],int(data['repeats_annually']),data['year'],oid))
            return self.out(conn,self.own(conn,uid,oid))

    def sharing(self,uid,oid,data):
        with self.db.transaction(True) as conn:
            row=self.own(conn,uid,oid)
            if row['version']!=data['version']:
                conflict()
            for share in data['sharing']:
                self.party(conn,uid,share['circle_id'])
            conn.execute('UPDATE occasion_sharing SET share_date=0,suggest=0,version=version+1 WHERE occasion_id=?',(oid,))
            for share in data['sharing']:
                conn.execute('INSERT INTO occasion_sharing(occasion_id,party_id,share_date,suggest) VALUES(?,?,?,?) ON CONFLICT(occasion_id,party_id) DO UPDATE SET share_date=excluded.share_date,suggest=excluded.suggest',(oid,share['circle_id'],int(share['share_date']),int(share['suggest'])))
            conn.execute('UPDATE occasions SET version=version+1 WHERE id=?',(oid,))
            return self.out(conn,self.own(conn,uid,oid))

    def shared_dates(self,uid,pid):
        with self.db.transaction() as conn:
            self.party(conn,uid,pid)
            items=[]
            for row in conn.execute('SELECT o.* FROM occasions o JOIN occasion_sharing s ON s.occasion_id=o.id WHERE s.party_id=? AND s.share_date=1 AND o.deleted=0 ORDER BY o.month,o.day,o.id',(pid,)):
                share=permitted_share(conn,row,pid)
                if share:
                    items.append(dict(id=row['id'],owner=user_out(conn.execute('SELECT * FROM users WHERE id=?',(row['user_id'],)).fetchone()),kind=row['kind'],name=row['name'],month=row['month'],day=row['day'],repeats_annually=bool(row['repeats_annually']),year=row['year'],next_occurrence=self.occurrence(row),suggestions_enabled=bool(share['suggest'])))
                if len(items)==100:
                    break
            return {'items':items}

    @staticmethod
    def suggestion_id(oid,pid,year):
        return digest(dump([oid,pid,year]))[:32]

    def candidates(self,conn,uid,row,party,occurrence):
        if not occurrence:
            return [],'今日から30日以内の記念日になると候補を確認できます。'
        context=self.discovery.circle_context(conn,party['id'])
        if context[1] and context[1].get('date_start') and context[1]['date_start']!=occurrence['occurrence_date']:
            return [],'講で確認した日付と異なります。旅行条件の日付を確認してください。'
        prefs=conn.execute('SELECT p.tags FROM preferences p JOIN grants g ON g.user_id=p.user_id WHERE p.user_id=? AND g.community_id=? AND g.use_matching=1',(row['user_id'],party['community_id'])).fetchone()
        personal=set(json.loads(prefs['tags'])) if prefs else set()
        references={}
        def eligible():
            for planrow in conn.execute("SELECT p.* FROM provider_plans p JOIN providers v ON v.id=p.provider_id WHERE p.status='published' AND v.active=1 ORDER BY p.id"):
                plan=self.market.plan_out(conn,planrow)
                schedule,date_reasons,excluded,date_unknowns=schedule_match(plan,occurrence['occurrence_date'])
                if excluded:
                    continue
                matched=self.discovery.relevance(conn,plan,party['id'],personal,context)
                if not matched['eligible']:
                    continue
                reasons=matched['reasons'] if uid==row['user_id'] else [reason for reason in matched['reasons'] if not reason.startswith('あなたが許可した関心')]
                if not reasons:
                    reasons=['公開されている旅行プラン。講で内容を確認できます']
                provider_id=planrow['provider_id']
                if provider_id not in references:
                    references[provider_id]=public_summary(conn,provider_id)
                yield dict(plan=plan,score=matched['score'],reasons=list(dict.fromkeys(reasons+date_reasons)),unknowns=list(dict.fromkeys(matched['unknowns']+date_unknowns)),match_status='needs_confirmation',schedule_status=schedule,experience_reference=references[provider_id])
        items=heapq.nsmallest(100,eligible(),key=lambda item:(-item['score'],-item['experience_reference']['ranking_signal'],item['plan']['starts_at'] or '9999',item['plan']['id']))
        return items,'登録された公開プランを条件と照合しています。記念日特典・空席・予約は未確認です。'

    def suggestion_out(self,conn,uid,row,party,occurrence,shared=True):
        sid=self.suggestion_id(row['id'],party['id'],occurrence['occurrence_year']) if occurrence else 'preview-'+row['id']
        status=conn.execute('SELECT state,version FROM occasion_suggestion_states WHERE suggestion_id=? AND user_id=?',(sid,uid)).fetchone() if shared else None
        candidates,notice=self.candidates(conn,uid,row,party,occurrence)
        return dict(id=sid,occasion_id=row['id'],owner=user_out(conn.execute('SELECT * FROM users WHERE id=?',(row['user_id'],)).fetchone()),name=row['name'],kind=row['kind'],occurrence=occurrence,circle_id=party['id'],occasion_version=row['version'],state=status['state'] if status else 'new',version=status['version'] if status else 0,shared=shared,candidates=candidates,notice=notice)

    def suggestions(self,uid,pid):
        with self.db.transaction(True) as conn:
            party=self.party(conn,uid,pid)
            eligible=[]
            for row in conn.execute('SELECT o.* FROM occasions o JOIN occasion_sharing s ON s.occasion_id=o.id WHERE s.party_id=? AND s.share_date=1 AND s.suggest=1 AND o.deleted=0',(pid,)):
                occurrence=self.occurrence(row)
                if occurrence and permitted_share(conn,row,pid,True):
                    eligible.append((row,occurrence))
            eligible.sort(key=lambda entry:(entry[1]['occurrence_date'],entry[0]['id']))
            items=[]
            for row,occurrence in eligible[:100]:
                sid=self.suggestion_id(row['id'],pid,occurrence['occurrence_year'])
                conn.execute('INSERT OR IGNORE INTO occasion_suggestions VALUES(?,?,?,?)',(sid,row['id'],pid,occurrence['occurrence_year']))
                items.append(self.suggestion_out(conn,uid,row,party,occurrence))
            return {'items':items}

    def preview(self,uid,oid,pid):
        with self.db.transaction() as conn:
            row=self.own(conn,uid,oid)
            party=self.party(conn,uid,pid)
            return self.suggestion_out(conn,uid,row,party,self.occurrence(row),False)

    def access_suggestion(self,conn,uid,sid):
        suggestion=require(conn.execute('SELECT * FROM occasion_suggestions WHERE id=?',(sid,)).fetchone())
        party=self.party(conn,uid,suggestion['party_id'])
        row=require(conn.execute('SELECT * FROM occasions WHERE id=? AND deleted=0',(suggestion['occasion_id'],)).fetchone())
        share=require(permitted_share(conn,row,party['id'],True))
        occurrence=require(self.occurrence(row))
        if occurrence['occurrence_year']!=suggestion['occurrence_year']:
            raise HTTPException(404,'現在の記念日の提案を開いてください。')
        return row,party,share,occurrence

    def state(self,uid,sid,data):
        with self.db.transaction(True) as conn:
            row,party,_,occurrence=self.access_suggestion(conn,uid,sid)
            previous=conn.execute('SELECT version FROM occasion_suggestion_states WHERE suggestion_id=? AND user_id=?',(sid,uid)).fetchone()
            if data['version']!=(previous['version'] if previous else 0):
                conflict()
            conn.execute('INSERT INTO occasion_suggestion_states VALUES(?,?,?,1) ON CONFLICT(suggestion_id,user_id) DO UPDATE SET state=excluded.state,version=occasion_suggestion_states.version+1',(sid,uid,data['state']))
            return self.suggestion_out(conn,uid,row,party,occurrence)

    def save(self,uid,sid,data):
        with self.db.transaction(True) as conn:
            row,party,share,occurrence=self.access_suggestion(conn,uid,sid)
            if row['version']!=data['occasion_version']:
                conflict()
            # Never let an old send key bypass current consent or plan eligibility.
            planrow=require(conn.execute("SELECT * FROM provider_plans WHERE id=? AND status='published'",(data['plan_id'],)).fetchone())
            if planrow['version']!=data['plan_version']:
                conflict()
            candidates,_=self.candidates(conn,uid,row,party,occurrence)
            candidate=next((item for item in candidates if item['plan']['id']==data['plan_id']),None)
            if not candidate:
                raise HTTPException(409,'公開状態・開催日・講の条件が変わりました。候補を開き直してください。')
            operation='occasion:card:'+sid
            previous,fingerprint=self.market.replay(conn,uid,operation,data)
            if previous:
                return self.discovery.card_out(conn,require(conn.execute('SELECT * FROM circle_candidate_cards WHERE id=?',(previous,)).fetchone()))
            card=conn.execute('SELECT * FROM circle_candidate_cards WHERE party_id=? AND plan_id=?',(party['id'],data['plan_id'])).fetchone()
            if card is None:
                if conn.execute('SELECT COUNT(*) FROM circle_candidate_cards WHERE party_id=?',(party['id'],)).fetchone()[0]>=100:
                    raise HTTPException(409,'この講へ保存できる候補は100件までです。')
                cardid=identifier()
                conn.execute('INSERT INTO circle_candidate_cards VALUES(?,?,?,?,?,?,?,1)',(cardid,party['id'],data['plan_id'],data['plan_version'],dump(candidate['plan']),uid,now()))
                conn.execute('INSERT INTO occasion_card_state VALUES(?,0)',(cardid,))
            else:
                cardid=card['id']
            conn.execute('INSERT INTO occasion_card_origins VALUES(?,?,?,?,?,?) ON CONFLICT(card_id,occasion_id,occurrence_year) DO UPDATE SET occasion_version=excluded.occasion_version,sharing_version=excluded.sharing_version',(cardid,row['id'],party['id'],occurrence['occurrence_year'],row['version'],share['version']))
            self.market.remember(conn,uid,operation,data,fingerprint,cardid)
            return self.discovery.card_out(conn,conn.execute('SELECT * FROM circle_candidate_cards WHERE id=?',(cardid,)).fetchone())
