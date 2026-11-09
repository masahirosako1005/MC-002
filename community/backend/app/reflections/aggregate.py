import json
from collections import Counter

from .extraction import ASPECTS, METHOD


def current_participants(conn,row):
    return [record[0] for record in conn.execute("""SELECT u.id FROM travel_party_members pm JOIN travel_parties p ON p.id=pm.party_id
        JOIN memberships m ON m.community_id=p.community_id AND m.user_id=pm.user_id AND m.status='active'
        JOIN users u ON u.id=pm.user_id AND u.login_enabled=1
        WHERE pm.party_id=? AND NOT EXISTS(SELECT 1 FROM provider_staff st WHERE st.provider_id=? AND st.user_id=u.id)
        ORDER BY u.id""",(row['party_id'],row['provider_id']))]


def state(conn,row):
    targets=json.loads(row['participants_json'])
    current=current_participants(conn,row)
    participants=conn.execute('SELECT * FROM reflection_participants WHERE reflection_id=? AND epoch=? ORDER BY user_id',(row['id'],row['epoch'])).fetchall()
    same=bool(row['participants_valid']) and targets==current and len(participants)==len(targets) and bool(targets)
    used=sum(bool(p['used_service']) for p in participants)
    consented=sum(bool(p['consented']) for p in participants)
    ready=bool(row['trip_finished']) and same and used==len(targets) and consented==len(targets)
    return dict(targets=targets,participants=participants,participant_set_current=same,ready_for_analysis=ready,
                target_count=len(targets),usage_confirmed_count=used,consented_count=consented)


def effective(message):
    automatic=json.loads(message['auto_json']) if message['auto_json'] else None
    if not automatic or not automatic['eligible']:
        return [],automatic
    if message['override_json'] is not None and message['override_source_version']==message['source_version']:
        return json.loads(message['override_json']),automatic
    return automatic['values'],automatic


def public_summary(conn,provider_id):
    contributions={aspect:[] for aspect in ASPECTS}
    for reflection in conn.execute('SELECT * FROM reflection_sessions WHERE provider_id=?',(provider_id,)):
        status=state(conn,reflection)
        if not status['ready_for_analysis']:
            continue
        opinions={aspect:[] for aspect in ASPECTS}
        # Raw conversation bodies are deliberately not read by the aggregation path.
        messages=conn.execute('SELECT author_id,source_version,auto_json,override_json,override_source_version FROM reflection_messages WHERE reflection_id=? AND epoch=? AND deleted=0',(reflection['id'],reflection['epoch']))
        for message in messages:
            if message['author_id'] not in status['targets']:
                continue
            values,_=effective(message)
            for value in values:
                if value['sentiment']!='excluded':
                    opinions[value['aspect_id']].append((value['sentiment'],message['author_id']))
        for aspect,entries in opinions.items():
            if not entries:
                continue
            choices={value for value,_ in entries}
            sentiment='mixed' if 'mixed' in choices or len(choices)>1 else next(iter(choices))
            contributions[aspect].append((reflection['party_id'],sentiment,{author for _,author in entries}))
    facets=[]
    visible_trips=set()
    signals=[]
    for aspect,label in ASPECTS.items():
        entries=contributions[aspect]
        trips={trip for trip,_,_ in entries}
        authors=set().union(*(authors for _,_,authors in entries)) if entries else set()
        counts=Counter(sentiment for _,sentiment,_ in entries)
        publish=len(trips)>=3 and len(authors)>=3 and all(count>=3 for count in counts.values())
        if publish:
            categories=set(counts)
            result='mixed' if 'mixed' in categories or len(categories)>1 else next(iter(categories))
            summary={'positive':'肯定的な体験の振り返りが集まっています。','negative':'改善を求める体験の振り返りが集まっています。','mixed':'肯定・否定を含む異なる体験があり、見方が分かれています。'}[result]
            signals.append(1 if result=='positive' else -1 if result=='negative' else 0)
            visible_trips.update(trips)
            facets.append(dict(aspect_id=aspect,label=label,status=result,trip_count=len(trips),summary=summary))
        else:
            facets.append(dict(aspect_id=aspect,label=label,status='insufficient',trip_count=None,summary='少数の体験を特定しないため、参考情報の表示を保留しています。'))
    return dict(status='available' if visible_trips else 'insufficient',trip_count=len(visible_trips) if visible_trips else None,minimum_trip_count=3,
                facets=facets,method=METHOD,note='同意した旅行後の専用会話をローカル規則で整理し、本人の訂正も反映した参考情報です。実利用は本人申告です。未評価は低評価ではありません。',
                ranking_signal=sum(signals)/len(signals) if signals else 0)
