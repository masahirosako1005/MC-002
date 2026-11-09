import hashlib
import json

from fastapi import HTTPException

from ..database import identifier, now
from ..service import member, require, user_out
from .catalog import EVIDENCE_NOTE, PREFECTURE_BY_ID, PREFECTURES, badge_progress


def check_version(row, version):
    if row['version'] != version:
        raise HTTPException(409, '記録が更新されています。開き直して変更内容を確認してください。')


class JournalService:
    def __init__(self, database):
        self.db = database

    @staticmethod
    def owned_journey(conn, uid, jid):
        return require(conn.execute('SELECT * FROM journal_journeys WHERE id=? AND user_id=?', (jid, uid)).fetchone())

    @staticmethod
    def owned_visit(conn, uid, vid):
        return require(conn.execute('SELECT * FROM journal_visits WHERE id=? AND user_id=?', (vid, uid)).fetchone())

    @staticmethod
    def journey_out(conn, row):
        return {key: row[key] for key in ('id', 'title', 'version', 'created_at')} | {
            'visit_count': conn.execute('SELECT COUNT(*) FROM journal_visits WHERE journey_id=?', (row['id'],)).fetchone()[0]}

    @staticmethod
    def candidate(conn, mid):
        row = conn.execute('SELECT latitude,longitude FROM journal_location_candidates WHERE media_id=?', (mid,)).fetchone()
        return dict(row) if row else None

    @staticmethod
    def photo_visible(conn, row, viewer):
        if not row['media_id']:
            return False
        photo = conn.execute('SELECT user_id FROM media WHERE id=? AND deleted=0', (row['media_id'],)).fetchone()
        if not photo:
            return False
        if photo['user_id'] == viewer:
            return True
        return conn.execute("""SELECT 1 FROM post_media pm JOIN posts p ON p.id=pm.post_id
            JOIN memberships owner ON owner.user_id=p.user_id AND owner.community_id=p.community_id AND owner.status='active'
            JOIN memberships viewer ON viewer.user_id=? AND viewer.community_id=p.community_id AND viewer.status='active'
            WHERE pm.media_id=? AND p.community_id=? AND p.status='published'""",
                            (viewer, row['media_id'], row['community_id'])).fetchone() is not None

    def visit_out(self, conn, row, viewer):
        own = row['user_id'] == viewer
        result = {key: row[key] for key in ('id','journey_id','prefecture_id','visited_on','place_label','latitude','longitude',
                                          'media_id','source','visibility','community_id','version','created_at','updated_at')}
        result.update(confirmed=True, prefecture_name=PREFECTURE_BY_ID[row['prefecture_id']]['name'],
                      media_url='/api/media/' + row['media_id'] if self.photo_visible(conn, row, viewer) else None,
                      evidence_label='写真の位置候補を本人が確認' if row['source'] == 'exif' else '訪問場所を本人が入力・確認')
        if not own:
            # Shared achievements never disclose coordinates. Visit sharing is coarse too.
            result.update(latitude=None, longitude=None, media_id=None, journey_id=None)
        return result

    @staticmethod
    def replay(conn, uid, operation, data):
        payload = {k: v for k,v in data.items() if k != 'request_key'}
        digest = hashlib.sha256(json.dumps(payload, sort_keys=True, ensure_ascii=False).encode()).hexdigest()
        previous = conn.execute('SELECT * FROM operation_keys WHERE actor_id=? AND operation=? AND request_key=?',
                                (uid, operation, data['request_key'])).fetchone()
        if previous and previous['payload_hash'] != digest:
            raise HTTPException(409, '同じ送信キーで内容が変わっています。新しい操作として保存してください。')
        return previous, digest

    @staticmethod
    def remember(conn, uid, operation, data, digest, result_id):
        conn.execute('INSERT INTO operation_keys VALUES(?,?,?,?,?)', (uid, operation, data['request_key'], digest, result_id))

    def journeys(self, uid):
        with self.db.transaction() as conn:
            return {'items': [self.journey_out(conn, row) for row in conn.execute('SELECT * FROM journal_journeys WHERE user_id=? ORDER BY created_at DESC,id', (uid,))]}

    def create_journey(self, uid, data):
        with self.db.transaction(True) as conn:
            previous, digest = self.replay(conn, uid, 'journal-journey', data)
            if previous:
                row = conn.execute('SELECT * FROM journal_journeys WHERE id=? AND user_id=?', (previous['result_id'], uid)).fetchone()
                if row is None:
                    raise HTTPException(409, 'この送信で作成した旅は削除されています。')
                return self.journey_out(conn, row)
            if conn.execute('SELECT COUNT(*) FROM journal_journeys WHERE user_id=?', (uid,)).fetchone()[0] >= 100:
                raise HTTPException(409, '保存できる旅は100件までです。')
            jid = identifier()
            conn.execute('INSERT INTO journal_journeys VALUES(?,?,?,1,?)', (jid, uid, data['title'], now()))
            self.remember(conn, uid, 'journal-journey', data, digest, jid)
            return self.journey_out(conn, self.owned_journey(conn, uid, jid))

    def journey(self, uid, jid):
        with self.db.transaction() as conn:
            row = self.owned_journey(conn, uid, jid)
            return {'journey': self.journey_out(conn, row), 'visits': [self.visit_out(conn, visit, uid) for visit in conn.execute('SELECT * FROM journal_visits WHERE journey_id=? ORDER BY visited_on,id', (jid,))]}

    def change_journey(self, uid, jid, data, delete=False):
        with self.db.transaction(True) as conn:
            row = self.owned_journey(conn, uid, jid)
            check_version(row, data['version'])
            if delete:
                conn.execute('DELETE FROM journal_journeys WHERE id=?', (jid,))
                return {'ok': True}
            conn.execute('UPDATE journal_journeys SET title=?,version=version+1 WHERE id=?', (data['title'], jid))
            return self.journey_out(conn, self.owned_journey(conn, uid, jid))

    def validate_visit(self, conn, uid, data, vid=None):
        self.owned_journey(conn, uid, data['journey_id'])
        if data['visibility'] == 'community':
            member(conn, uid, data['community_id'])
        if data['media_id'] is not None:
            require(conn.execute('SELECT 1 FROM media WHERE id=? AND user_id=? AND deleted=0', (data['media_id'], uid)).fetchone())
            existing = conn.execute('SELECT id FROM journal_visits WHERE media_id=?', (data['media_id'],)).fetchone()
            if existing is not None and existing['id'] != vid:
                raise HTTPException(409, 'この写真には訪問記録があります。既存の記録を編集してください。')
        if data['source'] == 'exif':
            candidate = self.candidate(conn, data['media_id'])
            prior = self.owned_visit(conn, uid, vid) if vid else None
            retained = prior is not None and prior['source'] == 'exif' and prior['media_id'] == data['media_id'] and all(
                prior[key] == data[key] for key in ('latitude','longitude'))
            if not retained and (candidate is None or any(abs(candidate[key] - data[key]) > 0.000001 for key in ('latitude','longitude'))):
                raise HTTPException(422, '写真の位置候補と一致しません。手入力の場所として確認してください。')

    def create_visit(self, uid, data):
        with self.db.transaction(True) as conn:
            previous, digest = self.replay(conn, uid, 'journal-visit', data)
            if previous:
                row = conn.execute('SELECT * FROM journal_visits WHERE id=? AND user_id=?', (previous['result_id'], uid)).fetchone()
                if row is None:
                    raise HTTPException(409, 'この送信で作成した訪問は削除されています。')
                return self.visit_out(conn, row, uid)
            self.validate_visit(conn, uid, data)
            if conn.execute('SELECT COUNT(*) FROM journal_visits WHERE user_id=?', (uid,)).fetchone()[0] >= 1000:
                raise HTTPException(409, '保存できる訪問は1000件までです。')
            vid, at = identifier(), now()
            fields = ('journey_id','prefecture_id','visited_on','place_label','latitude','longitude','media_id','source','visibility','community_id')
            conn.execute('INSERT INTO journal_visits VALUES(?,?,?,?,?,?,?,?,?,?,?,?,1,?,?)',
                         (vid, uid, *(data[key] for key in fields), at, at))
            self.remember(conn, uid, 'journal-visit', data, digest, vid)
            return self.visit_out(conn, self.owned_visit(conn, uid, vid), uid)

    def change_visit(self, uid, vid, data, delete=False):
        with self.db.transaction(True) as conn:
            row = self.owned_visit(conn, uid, vid)
            check_version(row, data['version'])
            if delete:
                conn.execute('DELETE FROM journal_visits WHERE id=?', (vid,))
                return {'ok': True}
            self.validate_visit(conn, uid, data, vid)
            fields = ('journey_id','prefecture_id','visited_on','place_label','latitude','longitude','media_id','source','visibility','community_id')
            conn.execute('UPDATE journal_visits SET journey_id=?,prefecture_id=?,visited_on=?,place_label=?,latitude=?,longitude=?,media_id=?,source=?,visibility=?,community_id=?,version=version+1,updated_at=? WHERE id=?',
                         (*(data[key] for key in fields), now(), vid))
            return self.visit_out(conn, self.owned_visit(conn, uid, vid), uid)

    def media(self, uid):
        with self.db.transaction() as conn:
            return {'items': [dict(id=row['id'], url='/api/media/'+row['id'], width=row['width'], height=row['height'],
                                   location_candidate=self.candidate(conn, row['id'])) for row in conn.execute('SELECT * FROM media WHERE user_id=? AND deleted=0 ORDER BY created_at DESC,id LIMIT 200', (uid,))]}

    def location_candidate(self, uid, mid, delete=False):
        with self.db.transaction(delete) as conn:
            require(conn.execute('SELECT 1 FROM media WHERE id=? AND user_id=? AND deleted=0', (mid,uid)).fetchone())
            if delete:
                conn.execute('DELETE FROM journal_location_candidates WHERE media_id=?', (mid,))
                return {'ok': True}
            return {'location_candidate': self.candidate(conn, mid)}

    def people(self, uid, cid):
        with self.db.transaction() as conn:
            member(conn, uid, cid)
            return {'items': [user_out(row) for row in conn.execute("SELECT u.* FROM users u JOIN memberships m ON m.user_id=u.id WHERE m.community_id=? AND m.status='active' AND u.login_enabled=1 ORDER BY u.id", (cid,))]}

    def profile_out(self, conn, uid, target):
        own = uid == target
        user = require(conn.execute('SELECT * FROM users WHERE id=? AND login_enabled=1', (target,)).fetchone())
        if not own:
            require(conn.execute("""SELECT 1 FROM memberships a JOIN memberships b ON a.community_id=b.community_id
                WHERE a.user_id=? AND b.user_id=? AND a.status='active' AND b.status='active'""", (uid,target)).fetchone())
        settings = conn.execute('SELECT * FROM journal_profiles WHERE user_id=?', (target,)).fetchone()
        sharing = bool(settings['share_achievements']) if settings else False
        visited = {row[0] for row in conn.execute('SELECT DISTINCT prefecture_id FROM journal_visits WHERE user_id=?', (target,))} if own or sharing else set()
        if own:
            visits = conn.execute('SELECT * FROM journal_visits WHERE user_id=? ORDER BY visited_on DESC,id', (target,)).fetchall()
        else:
            visits = conn.execute("""SELECT v.* FROM journal_visits v
                JOIN memberships owner ON owner.user_id=v.user_id AND owner.community_id=v.community_id AND owner.status='active'
                JOIN memberships viewer ON viewer.user_id=? AND viewer.community_id=v.community_id AND viewer.status='active'
                WHERE v.user_id=? AND v.visibility='community' ORDER BY v.visited_on DESC,v.id""", (uid,target)).fetchall()
        return dict(user=user_out(user), is_owner=own, share_achievements=sharing,
                    version=settings['version'] if settings else 1,
                    visited_prefectures=[p for p in PREFECTURES if p['id'] in visited],
                    badges=badge_progress(visited) if own or sharing else [],
                    shared_visits=[self.visit_out(conn, row, uid) for row in visits], evidence_note=EVIDENCE_NOTE)

    def profile(self, uid, target=None, data=None):
        target = target or uid
        with self.db.transaction(data is not None) as conn:
            if data is not None:
                conn.execute('INSERT OR IGNORE INTO journal_profiles(user_id) VALUES(?)', (uid,))
                row = conn.execute('SELECT * FROM journal_profiles WHERE user_id=?', (uid,)).fetchone()
                check_version(row, data['version'])
                conn.execute('UPDATE journal_profiles SET share_achievements=?,version=version+1 WHERE user_id=?', (int(data['share_achievements']),uid))
            return self.profile_out(conn, uid, target)
