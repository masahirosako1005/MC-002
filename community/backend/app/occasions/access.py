def permitted_share(conn,occasion,pid,suggestions=False):
    if occasion['deleted']:
        return None
    row=conn.execute("""SELECT s.* FROM occasion_sharing s
        JOIN travel_parties p ON p.id=s.party_id
        JOIN travel_party_members pm ON pm.party_id=p.id AND pm.user_id=?
        JOIN memberships m ON m.community_id=p.community_id AND m.user_id=pm.user_id AND m.status='active'
        JOIN users u ON u.id=pm.user_id AND u.login_enabled=1
        WHERE s.occasion_id=? AND s.party_id=? AND s.share_date=1 AND p.status='open'
        AND (p.ko_group_id IS NULL OR EXISTS(SELECT 1 FROM group_members gm WHERE gm.group_id=p.ko_group_id AND gm.user_id=u.id))""",(occasion['user_id'],occasion['id'],pid)).fetchone()
    if row and (not suggestions or row['suggest']):
        return row
    return None


def card_visible(conn,card_id):
    state=conn.execute('SELECT independent FROM occasion_card_state WHERE card_id=?',(card_id,)).fetchone()
    if state is None or state['independent']:
        return True
    for origin in conn.execute('SELECT * FROM occasion_card_origins WHERE card_id=?',(card_id,)):
        occasion=conn.execute('SELECT * FROM occasions WHERE id=?',(origin['occasion_id'],)).fetchone()
        share=permitted_share(conn,occasion,origin['party_id'],True) if occasion else None
        if share and occasion['version']==origin['occasion_version'] and share['version']==origin['sharing_version']:
            return True
    return False


def independent_save(conn,card_id):
    conn.execute('UPDATE occasion_card_state SET independent=1 WHERE card_id=?',(card_id,))
