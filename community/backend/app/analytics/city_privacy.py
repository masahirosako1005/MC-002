from collections import Counter, defaultdict

from ..residence.catalog import DESTINATION
from .origins import grouped_visitors, visible_areas

THRESHOLD = 5
REASON = '5人未満の集団や内訳を差し引いて推測できないよう、この集計全体の数値を表示していません。'


def small(value):
    return 0 < value < THRESHOLD


def first_days(history):
    result = {}
    for row in history:
        uid = row['user_id']
        result[uid] = min(result.get(uid, row['day']), row['day'])
    return result


def repeat_users(rows, earliest):
    return {row['user_id'] for row in rows if earliest[row['user_id']] < row['day']}


def counts(rows, earliest):
    return dict(visitors=len({row['user_id'] for row in rows}),
        returning_visitors=len(repeat_users(rows, earliest)),
        visit_days=len({(row['user_id'], row['day']) for row in rows}),
        participations=len({(row['user_id'], row['outing_id']) for row in rows}))


def safe_period(rows, earliest):
    total = counts(rows, earliest)
    if any(small(value) for value in (total['visitors'], total['returning_visitors'], total['visitors'] - total['returning_visitors'])):
        return False
    memberships = defaultdict(set)
    for row in rows:
        memberships[row['user_id']].add(row['provider_id'])
    atoms = Counter(frozenset(value) for value in memberships.values())
    return not any(small(value) for value in atoms.values())


def origins(profiles, rows, earliest, period_safe):
    visitors = {row['user_id'] for row in rows}
    groups, missing, withheld = grouped_visitors(profiles, visitors)
    areas, suppressed = visible_areas(groups, repeat_users(rows, earliest), rows)
    consented = len(visitors) - missing - withheld
    allowed = period_safe and not suppressed and not any(small(value) for value in (missing, withheld, consented))
    status = ('available' if areas else 'no_data') if allowed else 'insufficient_sample'
    return dict(status=status, reason=None if allowed else REASON, destination=DESTINATION,
        total_visitors=len(visitors) if period_safe else None,
        consented_visitors=consented if allowed else None, missing_visitors=missing if allowed else None,
        withheld_visitors=withheld if allowed else None, suppressed_visitors=0 if allowed else None,
        areas=areas if allowed else [], privacy_threshold=THRESHOLD, definitions=[
            'N西市に明示登録された事業者で、N西市の対象経路を使った確認済み利用者の現在の居住地域です。',
            '市内の複数事業者を同じ人が利用しても来訪実人数は1人です。同じ日本時間の日に別の店を利用しただけでは再訪になりません。',
            '再訪は当期の利用より前の別の日本時間の日にも、市内で確認済み利用があることです。期間前の履歴も参照します。',
            '現在登録された市区町村の代表点です。個人住所、訪問当時の住所、実際の出発地・移動経路ではありません。',
            '本人の許可がある地域だけを使います。未登録・未共有・少人数内訳から推測できる場合は地図と関連母数をまとめて非表示にします。',
        ])
