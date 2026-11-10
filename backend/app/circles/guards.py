from fastapi import HTTPException


def reject_direct_selection(conn, party_id):
    row = conn.execute('SELECT mode FROM circle_rooms WHERE party_id=?', (party_id,)).fetchone()
    if (row and row['mode'] != 'legacy') or conn.execute('SELECT 1 FROM circle_provider_invitations WHERE party_id=?',(party_id,)).fetchone():
        raise HTTPException(409, '講で共有内容を確認し、事業者への参加依頼を送ってください。')


def reject_direct_close(conn, consultation_id):
    if conn.execute('SELECT 1 FROM circle_provider_invitations WHERE consultation_id=?',(consultation_id,)).fetchone():
        raise HTTPException(409, '講の事業者参加欄から共有会話を閉じてください。')


def require_active_shared_room(conn, consultation_id):
    row = conn.execute('SELECT i.status,p.status AS party_status,c.status AS consultation_status FROM circle_provider_invitations i JOIN travel_parties p ON p.id=i.party_id JOIN consultations c ON c.id=i.consultation_id WHERE i.consultation_id=?', (consultation_id,)).fetchone()
    if row and (row['status'] != 'accepted' or row['party_status'] != 'open' or row['consultation_status'] != 'open'):
        raise HTTPException(404, 'この共有会話には参加していません。')
