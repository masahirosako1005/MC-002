"""Read the populated localhost app; retain counts/timings, never personal rows.

Run after the pre/post seed preservation comparison, because signing in writes
session metadata. Credentials come from the caller environment, never reports.
"""
import json
import os
import traceback
from contextlib import closing
from pathlib import Path
from time import perf_counter

import httpx

ROOT = Path(__file__).resolve().parents[2]
RESULT = ROOT / 'artifacts/city/live-experience.json'
TIMES = []
CHECKS = {}


def get(client, path, expected=200):
    started = perf_counter()
    response = client.get('/api' + path)
    TIMES.append(round((perf_counter() - started) * 1000, 1))
    assert response.status_code == expected, f'Unexpected HTTP {response.status_code}'
    return response.json()


def client(name, password_variable):
    result = httpx.Client(base_url='http://127.0.0.1:8081', timeout=15,
                          headers={'Origin': 'http://127.0.0.1:8081'})
    response = result.post('/api/stage/login', json={
        'username': name, 'password': os.environ[password_variable],
    })
    assert response.status_code == 200, 'Local sign-in failed'
    session = response.json()
    result.headers['Authorization'] = 'Bearer ' + session['access_token']
    result.headers['X-CSRF-Token'] = session['csrf_token']
    return result


def visitor_checks(visitor):
    catalog = get(visitor, '/daytrip/catalog')
    choices = [row for row in catalog['routes'] if row['origin'] == '大阪駅']
    assert len(choices) >= 8
    me = get(visitor, '/daytrip/me')
    assert len(me['benefits']) >= 12 and me['completed_count'] >= 20
    assert sum(bool(row.get('provider_name') and row.get('plan_title') and row.get('route_ids')) for row in me['benefits']) >= 12
    journal = get(visitor, '/journal/profile/u-aoi')
    assert len(journal['shared_visits']) >= 20
    photos = sum(bool(row['media_id']) for row in journal['shared_visits'])
    assert photos >= 20
    circles = get(visitor, '/circles')['items']
    conversation = next(row for row in circles if row.get('active_provider_invitation')
                        and row['active_provider_invitation']['status'] == 'accepted'
                        and row['id'].startswith('ops26-'))
    internal = get(visitor, '/travel-parties/' + conversation['id'] + '/messages')
    shared = get(visitor, '/circle-provider-invitations/' + conversation['active_provider_invitation']['id'] + '/room')
    assert len(internal['items']) >= 3 and len(shared['messages']) >= 3
    CHECKS['visitor'] = dict(choices=len(choices), coupons=len(me['benefits']),
        completed=me['completed_count'], journal_records=len(journal['shared_visits']),
        photo_records=photos, circles=len(circles), internal_messages=len(internal['items']),
        shared_messages=len(shared['messages']))
    get(visitor, '/providers/forest-house/city-analytics', 404)


def provider_checks(provider):
    for days in (30, 90, 365):
        city = get(provider, f'/providers/forest-house/city-analytics?days={days}')
        assert city['scope'] == 'city' and city['provider_count'] >= 6
        assert city['summary']['visitors']['count'] >= 42
        assert len(city['providers']['items']) >= 6
        assert city['origins']['status'] == 'available'
        assert len(city['origins']['areas']) >= 6
        CHECKS['city_' + str(days)] = dict(
            providers=city['provider_count'], plans=city['published_plan_count'],
            visitors=city['summary']['visitors']['count'],
            returning=city['summary']['returning_visitors']['count'],
            regions=len(city['origins']['areas']), trend_buckets=len(city['trend']['items']))
    get(provider, '/providers/forest-house/analytics?days=90')
    get(provider, '/providers/shore-school/analytics?days=90', 404)
    CHECKS['access'] = 'visitor city denied; peer private analytics denied; own analytics available'


def main():
    error = None
    error_line = None
    try:
        with closing(client('aoi', 'KOU_VISITOR_PASSWORD')) as visitor:
            visitor_checks(visitor)
        with closing(client('forest', 'KOU_PROVIDER_PASSWORD')) as provider:
            provider_checks(provider)
    except Exception as exc:
        error = type(exc).__name__
        error_line = traceback.extract_tb(exc.__traceback__)[-1].lineno
    result = dict(passed=error is None, error_type=error, error_line=error_line, checks=CHECKS,
                  read_requests=len(TIMES), maximum_read_ms=max(TIMES, default=0),
                  timings_ms=TIMES, scope='Local populated app API reads; not browser or tourism-effect measurement.')
    RESULT.parent.mkdir(parents=True, exist_ok=True)
    RESULT.write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding='utf-8')
    print(json.dumps(result, ensure_ascii=False))
    raise SystemExit(0 if error is None else 1)


if __name__ == '__main__':
    main()
