from datetime import UTC, datetime

from fastapi import HTTPException

from ..database import TAGS
from ..daytrip.catalog import CITY_ROUTE_IDS
from ..marketplace.service import Marketplace
from .service import JST, object_json, timestamp

CITY_ID = 'n-nishi'
REGISTRY_PREFIX = 'city-provider:' + CITY_ID + ':'


def registered_providers(conn, uid, requester, database):
    Marketplace(database).staff(conn, uid, requester)
    rows = [dict(row) for row in conn.execute('''SELECT p.id,p.name,p.area,
        (SELECT COUNT(*) FROM provider_plans q WHERE q.provider_id=p.id AND q.status='published') AS published_plan_count
        FROM providers p JOIN settings s ON s.key=? || p.id AND s.value='1'
        WHERE p.active=1 ORDER BY p.id''', (REGISTRY_PREFIX,))]
    if requester not in {row['id'] for row in rows}:
        raise HTTPException(404, '市の集計を利用できる事業者ではありません。')
    return rows


def city_visits(conn, at):
    rows = conn.execute('''SELECT o.id AS outing_id,o.provider_id,o.route_json,o.starts_at,o.ends_at,a.user_id
        FROM daytrip_outings o JOIN providers p ON p.id=o.provider_id AND p.active=1
        JOIN settings s ON s.key=? || p.id AND s.value='1'
        JOIN provider_plans q ON q.id=o.plan_id AND q.provider_id=o.provider_id
        JOIN daytrip_participants a ON a.outing_id=o.id
        JOIN users visitor ON visitor.id=a.user_id AND visitor.login_enabled=1
        JOIN daytrip_participants witness ON witness.outing_id=o.id AND witness.user_id=a.confirmed_by
        JOIN users verifier ON verifier.id=witness.user_id AND verifier.login_enabled=1
        WHERE o.status IN ('reporting','confirmed')
          AND a.accepted=1 AND a.claimed=1 AND a.provider_verified=1 AND a.revoked=0
          AND a.confirmed_by!=a.user_id AND witness.accepted=1 AND witness.claimed=1 AND witness.revoked=0
          AND julianday(o.ends_at)<=julianday(?) AND julianday(o.starts_at)<julianday(o.ends_at)''',
        (REGISTRY_PREFIX, at.isoformat()))
    result = []
    for row in rows:
        if object_json(row['route_json']).get('id') not in CITY_ROUTE_IDS:
            continue
        start, end = timestamp(row['starts_at']), timestamp(row['ends_at'])
        if start is None or end is None or not start < end <= at:
            continue
        result.append(dict(outing_id=row['outing_id'], provider_id=row['provider_id'], user_id=row['user_id'],
                           instant=end, day=end.astimezone(JST).date()))
    return result


def profiles(conn):
    return {row['user_id']: row for row in conn.execute('''
        SELECT DISTINCT r.user_id,r.area_id,r.share_analytics,u.login_enabled
        FROM residence_profiles r JOIN users u ON u.id=r.user_id
        JOIN daytrip_participants a ON a.user_id=r.user_id
        JOIN daytrip_outings o ON o.id=a.outing_id
        JOIN providers p ON p.id=o.provider_id AND p.active=1
        JOIN settings s ON s.key=? || p.id AND s.value='1' ''', (REGISTRY_PREFIX,))}


def plan_categories(conn):
    counts = dict.fromkeys(TAGS, 0)
    for row in conn.execute('''SELECT q.body FROM provider_plans q
        JOIN providers p ON p.id=q.provider_id AND p.active=1
        JOIN settings s ON s.key=? || p.id AND s.value='1' WHERE q.status='published' ''', (REGISTRY_PREFIX,)):
        tags = object_json(row['body']).get('tags', [])
        if isinstance(tags, list):
            for tag in set(item for item in tags if isinstance(item, str)) & TAGS.keys():
                counts[tag] += 1
    return [dict(id=key, label=label, plan_count=counts[key]) for key, label in TAGS.items()]


def clock_now():
    return datetime.now(UTC)
