import secrets

from fastapi import HTTPException

from ..database import identifier, now, password_hash
from ..marketplace.service import conflict
from ..password_policy import validate_new_password
from ..service import require, user_out
from .catalog import AREA_BY_ID


def valid_area(area_id):
    if area_id is not None and area_id not in AREA_BY_ID:
        raise HTTPException(422, '登録されている市区町村を選んでください。')


def profile(conn, uid):
    row = conn.execute('SELECT area_id,share_analytics,version,updated_at FROM residence_profiles WHERE user_id=?', (uid,)).fetchone()
    if row is None:
        return dict(area=None, share_area_analytics=False, version=0, updated_at=None)
    return dict(area=AREA_BY_ID.get(row['area_id']), share_area_analytics=bool(row['share_analytics']),
                version=row['version'], updated_at=row['updated_at'])


class ResidenceService:
    def __init__(self, database):
        self.db = database

    def register(self, data):
        valid_area(data.residence_area_id)
        validate_new_password(data.password.get_secret_value(), data.username)
        uid, salt = identifier(), secrets.token_hex(16)
        hashed = password_hash(data.password.get_secret_value(), salt)
        with self.db.transaction(True) as conn:
            if conn.execute('SELECT 1 FROM users WHERE username=?', (data.username,)).fetchone():
                raise HTTPException(409, 'この利用者名は使われています。別の利用者名を入力してください。')
            conn.execute('INSERT INTO users VALUES(?,?,?,?,?,?,?,1)',
                (uid, data.username, data.name, data.name[:1], '#805A46', salt, hashed))
            conn.execute("INSERT INTO preferences(user_id,tags,learn_from_posts) VALUES(?,'[]',0)", (uid,))
            conn.execute('INSERT INTO residence_profiles VALUES(?,?,?,1,?)',
                (uid, data.residence_area_id, int(data.share_area_analytics), now()))
            row = conn.execute('SELECT * FROM users WHERE id=?', (uid,)).fetchone()
            return dict(user=user_out(row), residence=profile(conn, uid), login_required=True)

    def me(self, uid, data=None):
        with self.db.transaction(data is not None) as conn:
            require(conn.execute('SELECT 1 FROM users WHERE id=? AND login_enabled=1', (uid,)).fetchone())
            if data is not None:
                valid_area(data.residence_area_id)
                current = profile(conn, uid)
                if current['version'] != data.version:
                    conflict()
                conn.execute('''INSERT INTO residence_profiles VALUES(?,?,?,?,?)
                    ON CONFLICT(user_id) DO UPDATE SET area_id=excluded.area_id,
                    share_analytics=excluded.share_analytics,version=excluded.version,updated_at=excluded.updated_at''',
                    (uid, data.residence_area_id, int(data.share_area_analytics), data.version + 1, now()))
            return profile(conn, uid)
