import json
import heapq

from fastapi import HTTPException
from ..database import TAGS, identifier, now
from ..marketplace.service import Marketplace, dump, conflict
from ..marketplace.schedules import schedule_state, schedule_match
from ..service import member, require, user_out
from ..reflections.aggregate import public_summary
from ..occasions.access import card_visible,independent_save


class Discovery:
    def __init__(self,database):
        self.db=database
        self.market=Marketplace(database)

    @staticmethod
    def circle_context(conn,pid):
        room=conn.execute('SELECT tags FROM circle_rooms WHERE party_id=?',(pid,)).fetchone()
        requirements=conn.execute('SELECT body,version FROM travel_requirements WHERE party_id=?',(pid,)).fetchone()
        return (set(json.loads(room['tags'])) if room else set(),
                json.loads(requirements['body']) if requirements else None,
                requirements['version'] if requirements else None)

    def relevance(self,conn,plan,pid=None,personal=None,context=None):
        group,requirements,_ = context if context is not None else (self.circle_context(conn,pid) if pid else (set(),None,None))
        confirmed=set(requirements['interests']) if requirements else set()
        tags=set(plan['tags'])
        matches=[(set(personal or []) & tags,2,'あなたが許可した関心'),(group & tags,3,'講で選んだ希望'),(confirmed & tags,3,'確認した旅行条件の関心')]
        reasons=[label+': '+'・'.join(TAGS[tag] for tag in sorted(common)) for common,_,label in matches if common]
        score=sum(len(common)*weight for common,weight,_ in matches)
        if requirements:
            match=self.market.match(requirements,plan)
            reasons+=match['reasons']
            unknowns=match['unknowns']
        else:
            _,_,excluded,date_unknowns=schedule_match(plan,None)
            match=dict(eligible=not excluded,excluded_reasons=excluded)
            unknowns=['人数・泊数・予算は講で確認してください','営業・空席・交通は未確認']+date_unknowns
        if not reasons:
            reasons=['公開されている旅行プラン。希望する内容を講で確かめられます']
        return dict(score=score,reasons=reasons,unknowns=unknowns,eligible=match['eligible'],excluded_reasons=match['excluded_reasons'])

    def discover(self,uid,cid,pid=None):
        with self.db.transaction() as conn:
            member(conn,uid,cid)
            if pid:
                party=self.market.party(conn,uid,pid)
                if party['community_id'] != cid:
                    raise HTTPException(404,'このコミュニティの講を選んでください。')
            preference=conn.execute('SELECT p.tags FROM preferences p JOIN grants g ON g.user_id=p.user_id WHERE p.user_id=? AND g.community_id=? AND g.use_matching=1',(uid,cid)).fetchone()
            personal=set(json.loads(preference['tags'])) if preference else set()
            context=self.circle_context(conn,pid) if pid else (set(),None,None)
            references={}
            def candidates():
                # Scan every public row before ranking; keep only the best 100 in memory.
                for row in conn.execute("SELECT p.* FROM provider_plans p JOIN providers v ON v.id=p.provider_id WHERE p.status='published' AND v.active=1 ORDER BY p.id"):
                    plan=self.market.plan_out(conn,row)
                    schedule=schedule_state(plan)
                    if schedule in ('ended','invalid'):
                        continue
                    matched=self.relevance(conn,plan,pid,personal,context)
                    if matched['eligible']:
                        provider_id=row['provider_id']
                        if provider_id not in references:
                            references[provider_id]=public_summary(conn,provider_id)
                        yield dict(plan=plan,score=matched['score'],reasons=matched['reasons'],unknowns=matched['unknowns'],match_status='needs_confirmation',schedule_status=schedule,experience_reference=references[provider_id])
            items=heapq.nsmallest(100,candidates(),key=lambda item:(-item['score'],-item['experience_reference']['ranking_signal'],item['plan']['starts_at'] or '9999',item['plan']['id']))
            return dict(items=items,context=dict(community_id=cid,circle_id=pid,profile_used=bool(personal),requirements_version=context[2]),method='consented-relevance-v1')

    def card_out(self,conn,row):
        current=conn.execute("SELECT p.* FROM provider_plans p JOIN providers v ON v.id=p.provider_id WHERE p.id=? AND p.status='published' AND v.active=1",(row['plan_id'],)).fetchone()
        plan=self.market.plan_out(conn,current) if current else None
        snapshot=json.loads(row['snapshot'])
        matched=self.relevance(conn,plan or snapshot,row['party_id'])
        if plan is None:
            state='unpublished'
        elif schedule_state(plan) in ('ended','invalid'):
            state='ended'
        elif not matched['eligible']:
            state='conditions_changed'
        elif row['plan_version'] != current['version']:
            state='updated'
        else:
            state='available'
        return dict(id=row['id'],circle_id=row['party_id'],plan_id=row['plan_id'],plan_version=row['plan_version'],snapshot=snapshot,
                    saved_by=user_out(conn.execute('SELECT * FROM users WHERE id=?',(row['saved_by'],)).fetchone()),created_at=row['created_at'],version=row['version'],
                    current_state=state,current_plan=plan,reasons=matched['reasons'],unknowns=matched['unknowns']+matched['excluded_reasons'])

    def cards(self,uid,pid,data=None):
        with self.db.transaction(data is not None) as conn:
            party=self.market.party(conn,uid,pid)
            if data is None:
                return {'items':[self.card_out(conn,row) for row in conn.execute('SELECT * FROM circle_candidate_cards WHERE party_id=? ORDER BY created_at DESC,id DESC LIMIT 100',(pid,)) if card_visible(conn,row['id'])]}
            if party['status'] != 'open':
                raise HTTPException(409,'この講の計画は閉じています。')
            operation='circle:candidate-card:'+pid
            previous,fingerprint=self.market.replay(conn,uid,operation,data)
            if previous:
                independent_save(conn,previous)
                return self.card_out(conn,require(conn.execute('SELECT * FROM circle_candidate_cards WHERE id=? AND party_id=?',(previous,pid)).fetchone()))
            existing=conn.execute('SELECT * FROM circle_candidate_cards WHERE party_id=? AND plan_id=?',(pid,data['plan_id'])).fetchone()
            if existing:
                origin=conn.execute('SELECT independent FROM occasion_card_state WHERE card_id=?',(existing['id'],)).fetchone()
                if origin and not origin['independent']:
                    planrow=require(conn.execute("SELECT p.* FROM provider_plans p JOIN providers v ON v.id=p.provider_id WHERE p.id=? AND p.status='published' AND v.active=1",(data['plan_id'],)).fetchone())
                    if planrow['version']!=data['plan_version']:
                        conflict()
                    plan=self.market.plan_out(conn,planrow)
                    if not self.relevance(conn,plan,pid)['eligible'] or schedule_state(plan) in ('ended','invalid'):
                        raise HTTPException(409,'現在の開催日時や講の条件に合いません。最新の候補を確認してください。')
                independent_save(conn,existing['id'])
                self.market.remember(conn,uid,operation,data,fingerprint,existing['id'])
                return self.card_out(conn,existing)
            planrow=require(conn.execute("SELECT p.* FROM provider_plans p JOIN providers v ON v.id=p.provider_id WHERE p.id=? AND p.status='published' AND v.active=1",(data['plan_id'],)).fetchone())
            if planrow['version'] != data['plan_version']:
                conflict()
            plan=self.market.plan_out(conn,planrow)
            matched=self.relevance(conn,plan,pid)
            if not matched['eligible'] or schedule_state(plan) in ('ended','invalid'):
                raise HTTPException(409,'現在の開催日時や講の条件に合いません。最新の候補を確認してください。')
            if conn.execute('SELECT COUNT(*) FROM circle_candidate_cards WHERE party_id=?',(pid,)).fetchone()[0] >= 100:
                raise HTTPException(409,'この講へ保存できる候補は100件までです。')
            cardid=identifier()
            conn.execute('INSERT INTO circle_candidate_cards VALUES(?,?,?,?,?,?,?,1)',(cardid,pid,plan['id'],plan['version'],dump(plan),uid,now()))
            self.market.remember(conn,uid,operation,data,fingerprint,cardid)
            return self.card_out(conn,conn.execute('SELECT * FROM circle_candidate_cards WHERE id=?',(cardid,)).fetchone())
