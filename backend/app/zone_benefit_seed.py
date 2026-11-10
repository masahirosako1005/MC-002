"""Explicit append-only budgeted coupon; existing coupons remain unchanged."""
import argparse
import json
from datetime import UTC, datetime, timedelta

from .config import Settings
from .database import Database
from .daytrip.zone_benefits import configure
from .marketplace.service import dump
from .operational_seed import PACK as OPERATING_PACK

PACK = 'zone-benefit-content-20261110-v1'
BENEFIT_ID = 'zone26-nnishi-reference'


def apply(database, at=None):
    instant = at or datetime.now(UTC)
    today = (instant + timedelta(hours=9)).date()
    with database.transaction(True) as conn:
        saved = conn.execute('SELECT value FROM settings WHERE key=?', (PACK,)).fetchone()
        if saved:
            return json.loads(saved['value']) | dict(already_applied=True)
        if not conn.execute('SELECT 1 FROM settings WHERE key=?', (OPERATING_PACK,)).fetchone():
            raise ValueError('Apply the operating content pack before the budgeted coupon')
        plan = conn.execute("SELECT * FROM provider_plans WHERE id='ops26-plan-0' AND status='published'").fetchone()
        if plan is None:
            raise ValueError('The published operating plan is unavailable')
        conn.execute('''INSERT INTO daytrip_benefits(id,provider_id,plan_id,title,min_rank,discount_type,
            discount_value,max_discount_yen,max_redemptions,starts_on,ends_on,status,created_at)
            VALUES(?,?,?,?,1,'percent',5,1000,200,?,?,'published',?)''',
            (BENEFIT_ID, plan['provider_id'], plan['id'], '門前朝市・20〜40km地域の追加割引',
             today.isoformat(), (today + timedelta(days=120)).isoformat(), instant.isoformat()))
        conn.execute('INSERT INTO settings VALUES(?,?)', ('daytrip-benefit-rank:' + BENEFIT_ID, 'R2'))
        benefit = conn.execute('SELECT * FROM daytrip_benefits WHERE id=?', (BENEFIT_ID,)).fetchone()
        state = configure(conn, benefit, dict(additional_percent=5, budget_yen=12000))
        result = dict(pack=PACK, applied_at=instant.isoformat(), already_applied=False,
                      benefit_id=BENEFIT_ID, policy=state, prior_rows_updated=0)
        conn.execute('INSERT INTO settings VALUES(?,?)', (PACK, dump(result)))
        return result


def main():
    parser = argparse.ArgumentParser(description='Append one explicitly requested budgeted coupon')
    parser.add_argument('--apply', action='store_true', required=True)
    parser.parse_args()
    print(json.dumps(apply(Database(Settings().db_path)), ensure_ascii=False))


if __name__ == '__main__':
    main()
