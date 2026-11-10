def test_pages_preserve_order_without_duplicates_and_hide_private_drafts(harness):
    aoi, ren = harness.client('aoi'), harness.client('ren')
    db = harness.app.state.database
    with db.transaction(True) as conn:
        for index in range(123):
            conn.execute("""INSERT INTO posts(id,user_id,community_id,body,tags,status,place_label,created_at)
                VALUES(?,?,'peers','記録','[]',?,'N西市',?)""", (
                    f'paging-{index:03}', 'u-aoi' if index != 122 else 'u-ren',
                    'published' if index < 121 else 'draft', '2026-01-01T01:00:00+00:00'))
    first = aoi.get('/communities/peers/feed?limit=24').json()
    assert len(first['items']) == 24 and first['next_cursor']
    # Newer records do not shift a keyset cursor while older pages are read.
    with db.transaction(True) as conn:
        conn.execute("""INSERT INTO posts(id,user_id,community_id,body,tags,status,place_label,created_at)
            VALUES('paging-new','u-aoi','peers','新しい記録','[]','published','N西市','2027-01-01T01:00:00+00:00')""")
    ids = [row['id'] for row in first['items']]
    cursor = first['next_cursor']
    while cursor:
        response = aoi.get('/communities/peers/feed', params={'before': cursor, 'limit': 24})
        assert response.status_code == 200
        page = response.json()
        ids.extend(row['id'] for row in page['items'])
        cursor = page['next_cursor']
    assert len(ids) == len(set(ids))
    assert {f'paging-{index:03}' for index in range(122)} <= set(ids)
    assert 'paging-new' not in ids and 'paging-122' not in ids
    assert aoi.get('/communities/peers/feed?before=paging-122').status_code == 404
    assert ren.get('/communities/peers/feed?before=paging-121').status_code == 404
    assert aoi.get('/communities/peers/feed?limit=101').status_code == 422
    assert aoi.get('/communities/peers/feed?limit=0').status_code == 422
    assert aoi.get('/communities/peers/feed?before=missing-record').status_code == 404
    with db.transaction(True) as conn:
        conn.execute("UPDATE memberships SET status='left' WHERE user_id='u-aoi' AND community_id='peers'")
    assert aoi.get('/communities/peers/feed', params={'before': first['next_cursor']}).status_code == 404
