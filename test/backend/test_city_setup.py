import json

from app.city_setup import apply
from app.daytrip.catalog import ROUTES


def test_city_conversion_is_explicit_repeatable_and_keeps_history(harness):
    db = harness.app.state.database
    with db.transaction(True) as conn:
        before = {table: [tuple(row) for row in conn.execute('SELECT * FROM '+table)]
                  for table in ('posts','media','consultation_messages','daytrip_outings')}
        conn.execute("UPDATE providers SET area='軽井沢周辺' WHERE id='forest-house'")
        row = conn.execute("SELECT body FROM provider_plans WHERE id='forest-six'").fetchone()
        body = json.loads(row['body'])
        body['area'] = '軽井沢周辺'
        conn.execute("UPDATE provider_plans SET body=? WHERE id='forest-six'", (json.dumps(body),))
    first = apply(db)
    second = apply(db)
    assert not first['already_applied'] and second['already_applied']
    assert first['changes'] == second['changes']
    with db.transaction() as conn:
        assert {r[0] for r in conn.execute('SELECT area FROM providers')} == {'N西市'}
        assert {json.loads(r[0])['area'] for r in conn.execute('SELECT body FROM provider_plans')} == {'N西市'}
        for table, rows in before.items():
            assert rows == [tuple(r) for r in conn.execute('SELECT * FROM '+table)]
        assert not conn.execute('PRAGMA foreign_key_check').fetchall()
    assert all(r['destination'].startswith('N西市') for r in ROUTES)
    assert all(r['distance_basis']=='fictional_planning_assumption' for r in ROUTES)
