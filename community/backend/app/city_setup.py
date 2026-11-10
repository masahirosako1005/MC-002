"""Explicit scenario conversion. Historical snapshots and messages are untouched."""
import argparse
import hashlib
import json

from .config import Settings
from .database import Database, now

MARKER = 'nnishi-city-20261110'
WORDS = {'軽井沢周辺': 'N西市', '軽井沢': 'N西市', '海辺のまち': 'N西市・川辺',
         '新百合ヶ丘': 'N西市・北山', '町田': 'N西市・門前町', '海辺': '川辺',
         '港の': '川沿いの', '浜の': '川辺の', '高原の': '北山の'}


def text(value):
    for old, new in WORDS.items():
        value = value.replace(old, new)
    return value


def checksum(value):
    return hashlib.sha256(json.dumps(value, sort_keys=True, ensure_ascii=False).encode()).hexdigest()


def convert_plan(body):
    body['area'] = 'N西市'
    for field in ('title', 'summary', 'price_note'):
        if isinstance(body.get(field), str):
            body[field] = text(body[field])
    for item in body.get('itinerary', []):
        for field in ('place', 'description'):
            if isinstance(item.get(field), str):
                item[field] = text(item[field])
    return body


def apply(database):
    with database.transaction(True) as conn:
        old = conn.execute('SELECT value FROM settings WHERE key=?', (MARKER,)).fetchone()
        if old:
            return {**json.loads(old['value']), 'already_applied': True}
        changed = []
        for row in conn.execute('SELECT * FROM providers').fetchall():
            if row['area'] != 'N西市':
                conn.execute("UPDATE providers SET area='N西市' WHERE id=?", (row['id'],))
                changed.append(dict(table='providers', before=checksum(dict(row)), after_area='N西市'))
        for row in conn.execute('SELECT * FROM provider_plans').fetchall():
            body = convert_plan(json.loads(row['body']))
            if body == json.loads(row['body']):
                continue
            conn.execute('UPDATE provider_plans SET body=?,version=version+1,updated_at=? WHERE id=?',
                         (json.dumps(body, ensure_ascii=False), now(), row['id']))
            changed.append(dict(table='provider_plans', before=checksum(dict(row)), after_body=checksum(body)))
        for old_id, new_id in (('shinjuku-machida-rail','osaka-nnishi-reference'),
                               ('shinjuku-shinyurigaoka-rail','suita-nnishi-reference')):
            count = conn.execute('UPDATE daytrip_plan_routes SET route_id=? WHERE route_id=?', (new_id,old_id)).rowcount
            if count:
                changed.append(dict(table='daytrip_plan_routes', count=count))
        report = dict(applied_at=now(), already_applied=False, changes=changed,
                      historical_snapshots_changed=False, destination='N西市', latitude=34.83, longitude=135.50)
        conn.execute('INSERT INTO settings VALUES(?,?)', (MARKER,json.dumps(report,ensure_ascii=False)))
        return report


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--apply', action='store_true', required=True)
    parser.parse_args()
    report = apply(Database(Settings().db_path))
    print(json.dumps({key:value for key,value in report.items() if key!='changes'},ensure_ascii=False))
