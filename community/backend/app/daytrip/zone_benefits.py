"""Private residence-based reference discounts; never geographic measurements."""
import json

from fastapi import HTTPException

from ..marketplace.service import dump
from .catalog import CITY_ROUTE_IDS

DISTANCE_VERSION = 'n-nishi-reference-2026-11-10-v1'
POLICY_PREFIX = 'daytrip-zone-policy:'
# Frozen values for DISTANCE_VERSION, from catalog.py's five reference routes.
# Changing the catalogue must not silently change this policy's distance basis.
AREA_DISTANCES = {'27100': 32.0, '27205': 24.0, '26100': 38.0, '28100': 40.0, '27140': 39.0}
DISTANCE_NOTE = '登録市区町村の代表駅からN西市への計画用参考値です。自宅からの実測・直線距離・確定した交通距離ではありません。'


def policy(conn, bid):
    row = conn.execute('SELECT value FROM settings WHERE key=?', (POLICY_PREFIX + bid,)).fetchone()
    return json.loads(row['value']) if row else None


def used_yen(conn, bid):
    return conn.execute("SELECT COALESCE(SUM(discount_yen),0) FROM daytrip_redemptions WHERE benefit_id=? AND status IN ('reserved','redeemed')", (bid,)).fetchone()[0]


def budget_status(conn, bid):
    saved = policy(conn, bid)
    if saved is None:
        return None
    used = used_yen(conn, bid)
    return saved | dict(used_yen=used, remaining_yen=max(0, saved['budget_yen'] - used))


def can_configure(conn, benefit):
    linked = conn.execute("SELECT r.route_id FROM daytrip_plan_routes r JOIN provider_plans p ON p.id=r.plan_id WHERE r.plan_id=? AND p.status='published'", (benefit['plan_id'],)).fetchone()
    return (benefit['discount_type'] == 'percent' and benefit['status'] == 'published'
            and linked is not None and linked['route_id'] in CITY_ROUTE_IDS)


def configure(conn, benefit, data):
    if not can_configure(conn, benefit):
        raise HTTPException(409, 'N西市の公開プランに対する、公開中の割合クーポンが対象です。')
    if data['budget_yen'] < used_yen(conn, benefit['id']):
        raise HTTPException(409, '予算は確保済み・利用済みの割引総額以上にしてください。')
    saved = dict(additional_percent=data['additional_percent'], budget_yen=data['budget_yen'],
                 distance_version=DISTANCE_VERSION)
    conn.execute('INSERT INTO settings(key,value) VALUES(?,?) ON CONFLICT(key) DO UPDATE SET value=excluded.value',
                 (POLICY_PREFIX + benefit['id'], dump(saved)))
    conn.execute('UPDATE daytrip_benefits SET version=version+1 WHERE id=?', (benefit['id'],))
    return budget_status(conn, benefit['id']) | dict(version=benefit['version'] + 1)


def residence_distance(conn, uid):
    # Consent to aggregated analytics is deliberately not read here. This
    # private benefit evaluation neither shares nor changes that consent.
    row = conn.execute('SELECT area_id FROM residence_profiles WHERE user_id=?', (uid,)).fetchone()
    if row is None or row['area_id'] is None:
        return None, '市区町村が未登録のため基本の割引率です。'
    distance = AREA_DISTANCES.get(row['area_id'])
    if distance is None:
        return None, '登録地域の参考距離が未設定のため基本の割引率です。'
    return distance, ('片道20〜40kmの対象地域です。' if 20 <= distance <= 40
                      else '片道20〜40kmの対象外のため基本の割引率です。')


def personal_offer(conn, uid, benefit, original_yen):
    saved = policy(conn, benefit['id'])
    if saved is None:
        return None
    distance, reason = residence_distance(conn, uid)
    eligible = distance is not None and 20 <= distance <= 40
    additional = saved['additional_percent'] if eligible else 0
    rate = min(100, benefit['discount_value'] + additional)
    discount = min(original_yen, original_yen * rate // 100, benefit['max_discount_yen'])
    return dict(eligible=eligible, reason=reason, base_percent=benefit['discount_value'],
                effective_percent=rate, target_percent=min(100, benefit['discount_value'] + saved['additional_percent']),
                additional_percent=additional, one_way_km=distance,
                distance_version=saved['distance_version'], distance_basis='fictional_planning_assumption',
                distance_note=DISTANCE_NOTE, discount_yen=discount,
                can_reserve=used_yen(conn, benefit['id']) + discount <= saved['budget_yen'])


def reservation_discount(conn, uid, benefit, original_yen):
    offer = personal_offer(conn, uid, benefit, original_yen)
    if offer is not None:
        if not offer['can_reserve']:
            raise HTTPException(409, 'このクーポンの割引予算が不足しています。')
        return offer['discount_yen'], offer
    raw = benefit['discount_value'] if benefit['discount_type'] == 'amount' else original_yen * benefit['discount_value'] // 100
    return min(original_yen, raw, benefit['max_discount_yen']), None
