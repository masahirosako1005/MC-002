from datetime import date
import json
import re
import unicodedata

from fastapi import HTTPException
from pydantic import ValidationError
from ..database import identifier, now
from ..marketplace.schemas import RequirementsInput
from ..marketplace.service import dump
from ..service import require

HELP = dict(method='local-catalog-rules-v1',external_ai_enabled=False,
            description='PC内の公開プランと、数値・日付・関心の整理規則を使って旅の条件を一緒に確かめます。',
            limitations=['一般的な会話を理解する生成AIではありません。','否定・引用・複数の条件は読み違えることがあります。確認して保存してください。',
                         '営業・空席・交通や外部の旅行情報は取得しません。','会話だけでは参加招待や事業者への共有を行いません。'])

ALIASES = {'mountain':('山','登山'),'nature':('森','自然'),'cafe':('カフェ','喫茶'),
           'food':('食事','ごはん','食べ歩き'),'coast':('海','浜'),'walk':('街歩き','散歩'),
           'fashion':('服','ファッション'),'games':('ゲーム',),'stay':('宿','温泉')}


def extract_conditions(text, previous):
    text = unicodedata.normalize('NFKC',text)
    result = dict(previous)
    ambiguities = []
    for key,label,pattern,limit in (('planned_people','人数',r'(\d+)\s*人',500),('nights','泊数',r'(\d+)\s*泊',30)):
        values = set()
        for match in re.finditer(pattern,text):
            if key == 'planned_people' and re.match(r'\s*(?:あたり|当たり|につき|ずつ|[\d.]+\s*万?円)',text[match.end():]):
                continue
            values.add(int(match.group(1)))
        if len(values) == 1:
            value = next(iter(values))
            if value <= limit and (key == 'nights' or value >= 1):
                result[key] = value
            else:
                result.pop(key,None)
                ambiguities.append(label+'が入力範囲外です')
        elif len(values) > 1:
            result.pop(key,None)
            ambiguities.append(label+'が複数あります')
    money = {round(float(value)*(10000 if unit else 1)) for value,unit in re.findall(r'(\d+(?:\.\d+)?)\s*(万)?円',text)}
    if len(money) == 1 and 1 <= next(iter(money)) <= 100_000_000:
        result['budget_yen'] = next(iter(money))
    elif money:
        result.pop('budget_yen',None)
        ambiguities.append('予算額を一つに確かめてください')
    per = bool(re.search(r'(1人|一人|ひとり|人あたり|人当たり)',text))
    total = bool(re.search(r'(全員|総額|合計|全体で)',text))
    if per != total:
        result['budget_basis'] = 'per_person' if per else 'party_total'
    elif per and total:
        result.pop('budget_basis',None)
        ambiguities.append('1人あたりか全員分かを確かめてください')
    plan_only = bool(re.search(r'(プラン部分|プラン代|プランのみ|交通費を除|交通費なし)',text))
    whole = bool(re.search(r'(旅行全体|交通費込み|交通費を含|すべて込み)',text))
    if plan_only != whole:
        result['budget_scope'] = 'plan_only' if plan_only else 'whole_trip'
    elif plan_only and whole:
        result.pop('budget_scope',None)
        ambiguities.append('費用に含む範囲を確かめてください')
    dates = set(re.findall(r'(\d{4})[-/年](\d{1,2})[-/月](\d{1,2})日?',text))
    if len(dates) == 1:
        try:
            result['date_start'] = date(*map(int,next(iter(dates)))).isoformat()
        except ValueError:
            result.pop('date_start',None)
            ambiguities.append('日付を確かめてください')
    elif len(dates) > 1:
        result.pop('date_start',None)
        ambiguities.append('希望日が複数あります')
    tags = set(result.get('interests',[]))
    for tag,words in ALIASES.items():
        for word in words:
            if word in text:
                if re.search(re.escape(word)+r'(?:は|を)?(?:なし|不要|除く|避け)',text):
                    tags.discard(tag)
                else:
                    tags.add(tag)
    result['interests'] = sorted(tags)
    if re.search(r'(ではなく|じゃなく|ではない|以外|仮に|たとえば|例えば)',text):
        # Do not let an unresolved example/negation silently become an old confirmed value next turn.
        for key,pattern in (('planned_people',r'\d+\s*人'),('nights',r'\d+\s*泊'),('budget_yen',r'円'),
                            ('budget_basis',r'(人|全員|総額|合計)'),('budget_scope',r'(交通費|プラン|旅行全体)'),
                            ('date_start',r'\d{4}[-/年]')):
            if re.search(pattern,text):
                result.pop(key,None)
        result['interests'] = list(previous.get('interests',[]))
        ambiguities.append('否定や例示を含みます。条件欄で意図を確認してください')
    return result,ambiguities


class AssistantMixin:
    def turns(self, uid, pid, data=None):
        with self.db.transaction(data is not None) as conn:
            self.party(conn,uid,pid,open_only=data is not None)
            if data is None:
                rows = conn.execute('SELECT body FROM circle_assistant_turns WHERE party_id=? ORDER BY created_at DESC,id DESC LIMIT 100',(pid,)).fetchall()
                return {'items':[json.loads(row['body']) for row in reversed(rows)]}
            operation = 'circle:assistant:'+pid
            previous,fingerprint = self.market.replay(conn,uid,operation,data)
            if previous:
                return json.loads(require(conn.execute('SELECT body FROM circle_assistant_turns WHERE id=? AND party_id=?',(previous,pid)).fetchone())['body'])
            if conn.execute('SELECT COUNT(*) FROM circle_assistant_turns WHERE party_id=?',(pid,)).fetchone()[0] >= 200:
                raise HTTPException(409,'この講の条件対話は200回までです。条件欄から調整できます。')
            stored = conn.execute('SELECT body,version FROM travel_requirements WHERE party_id=?',(pid,)).fetchone()
            version = stored['version'] if stored else 0
            last = conn.execute('SELECT body FROM circle_assistant_turns WHERE party_id=? ORDER BY created_at DESC,id DESC LIMIT 1',(pid,)).fetchone()
            prior = json.loads(last['body']) if last else None
            defaults = json.loads(stored['body']) if stored else {}
            if prior and prior['requirements_version'] == version:
                defaults = prior['proposed_conditions']
            conditions,ambiguities = extract_conditions(data['body'],defaults)
            conditions.setdefault('date_start',None)
            conditions.setdefault('departure_label','')
            missing = [label for key,label in [('planned_people','人数'),('nights','泊数'),('budget_yen','予算額'),('budget_basis','予算の単位'),('budget_scope','費用の範囲')] if conditions.get(key) is None]
            candidates = []
            if not missing and not ambiguities:
                try:
                    validated = RequirementsInput(**conditions,version=version).model_dump(mode='json')
                    for row in conn.execute("SELECT p.* FROM provider_plans p JOIN providers v ON v.id=p.provider_id WHERE p.status='published' AND v.active=1 ORDER BY p.id"):
                        plan = self.market.plan_out(conn,row)
                        matched = self.market.match(validated,plan)
                        if matched['eligible']:
                            candidates.append(dict(plan=plan,reasons=matched['reasons'],unknowns=matched['unknowns'],estimated_total_yen=matched['estimated_total_yen']))
                            if len(candidates)>=100:
                                break
                except ValidationError:
                    ambiguities.append('条件の値を確認してください')
            if ambiguities:
                reply = '条件を一つに決める前に、'+ '。'.join(ambiguities)+'。'
            elif missing:
                reply = 'ここまでの希望を残しました。'+ '・'.join(missing)+'を教えてください。例：6人、2泊、1人3万円、プラン部分。'
            elif candidates:
                reply = 'この条件の候補では、'+ '、'.join(item['plan']['title'] for item in candidates[:3])+'が人数・泊数・費用に合います。条件欄で確認して保存すると、行き先を選べます。'
            else:
                reply = '現在の公開プランに、この人数・泊数・予算を満たす候補はありません。条件を変えて相談するか、事業者の公開プランを確認できます。'
            result = dict(id=identifier(),user_body=data['body'],author_name=conn.execute('SELECT name FROM users WHERE id=?',(uid,)).fetchone()[0],
                          reply=reply,proposed_conditions=conditions,missing_fields=missing,ambiguities=ambiguities,candidates=candidates,
                          requirements_version=version,method=HELP['method'],needs_confirmation=True,created_at=now())
            conn.execute('INSERT INTO circle_assistant_turns VALUES(?,?,?,?,?)',(result['id'],pid,uid,dump(result),result['created_at']))
            self.market.remember(conn,uid,operation,data,fingerprint,result['id'])
            return result
