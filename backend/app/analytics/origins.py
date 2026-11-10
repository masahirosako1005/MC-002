from collections import defaultdict

from ..residence.catalog import AREA_BY_ID, DESTINATION

THRESHOLD = 5


def residences(conn, provider_id):
    # Read only profiles linked to this provider's saved outings; the caller
    # subsequently restricts to its confirmed visitors in the requested period.
    return {row['user_id']: row for row in conn.execute('''
        SELECT DISTINCT r.user_id,r.area_id,r.share_analytics,u.login_enabled
        FROM residence_profiles r JOIN users u ON u.id=r.user_id
        JOIN daytrip_participants a ON a.user_id=r.user_id
        JOIN daytrip_outings o ON o.id=a.outing_id WHERE o.provider_id=?''', (provider_id,))}


def grouped_visitors(profiles, visitors):
    groups = defaultdict(set)
    missing, withheld = 0, 0
    for uid in visitors:
        row = profiles.get(uid)
        if row is None or row['area_id'] not in AREA_BY_ID:
            missing += 1
        elif not row['share_analytics'] or not row['login_enabled']:
            withheld += 1
        else:
            groups[row['area_id']].add(uid)
    return groups, missing, withheld


def returning_users(visits, history):
    first, latest = {}, {}
    for row in history:
        uid = row['user_id']
        first[uid] = min(first.get(uid, row['instant']), row['instant'])
    for row in visits:
        uid = row['user_id']
        latest[uid] = max(latest.get(uid, row['instant']), row['instant'])
    return {uid for uid, ended in latest.items() if first.get(uid, ended) < ended}


def visible_areas(groups, repeat, visits):
    areas, suppressed = [], 0
    for area_id, users in sorted(groups.items()):
        count = len(users)
        returning = len(users & repeat)
        small_breakdown = any(0 < value < THRESHOLD for value in (returning, count - returning))
        if count < THRESHOLD or small_breakdown:
            # Never identify the city or its coordinates for a small cohort.
            # Hiding just the repeat count is insufficient when summary totals
            # allow its suppressed visit count to be reconstructed by subtraction.
            suppressed += count
            continue
        occurrences = len({(row['outing_id'], row['user_id']) for row in visits if row['user_id'] in users})
        areas.append(dict(AREA_BY_ID[area_id], visitors=count,
            returning_visitors=returning, visits=occurrences, returning_status='available'))
    return areas, suppressed


def origin_summary(conn, provider_id, visits, history):
    visitors = {row['user_id'] for row in visits}
    groups, missing, withheld = grouped_visitors(residences(conn, provider_id), visitors)
    areas, suppressed = visible_areas(groups, returning_users(visits, history), visits)
    consented = len(visitors) - missing - withheld
    return dict(status='available' if areas else 'insufficient_sample' if consented else 'no_data',
        destination=DESTINATION, total_visitors=len(visitors), consented_visitors=consented,
        missing_visitors=missing, withheld_visitors=withheld, suppressed_visitors=suppressed,
        areas=areas, privacy_threshold=THRESHOLD, definitions=[
            '実参加申告・参加者間の確認・事業者確認が揃った自社の終了済み開催だけを数えます。',
            '来訪者は当期の利用者の実人数です。再訪者は、当期の確認済み開催より前に自社の別開催で利用確認がある人です。期間内の2回目も含みます。',
            '位置は本人が現在登録した市区町村の代表点です。個人の所在地、訪問当時の住所、実際の出発地や移動経路を示しません。',
            '未設定には市区町村の未登録・対象外を、未共有には地域集計の許可がない人を数えます。許可の撤回は次回集計に反映します。',
            '市区町村ごとの来訪者が5人未満、又は再訪者・初回者のどちらかが1〜4人の場合、その地域を地図から除きます。',
            '5人未満の集団を表示しないルールです。重なる期間や異なる取得時刻の結果を比較した推測まで防ぐものではありません。',
            'N西市は大阪府内を想定した架空の目的地です。市区町村代表点と目的地を結ぶ線は実際の移動を観測したものではありません。',
        ])
