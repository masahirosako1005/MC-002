import secrets

from fastapi import HTTPException

from ..database import now, password_hash, password_matches
from ..password_policy import validate_new_password
from .schemas import PasswordChanged


class AccountService:
    def __init__(self, database):
        self.db = database

    def change_password(self, session, current_password, new_password, *, stage=False):
        # Only the authenticated dependency supplies the actor and token digest.
        # Never accept an account identifier from the request body.
        user_id = session["user_id"]
        with self.db.transaction() as conn:
            before = conn.execute(
                "SELECT username,salt,password_hash,login_enabled FROM users WHERE id=?", (user_id,),
            ).fetchone()
        if before is None or not before["login_enabled"]:
            raise HTTPException(401, "ログインしてください。")
        # The common bounded KDF runs outside any database transaction or lock.
        if not password_matches(current_password, before["salt"], before["password_hash"]):
            raise HTTPException(422, "現在のパスワードを確認してください。")
        if secrets.compare_digest(current_password.encode("utf-8"), new_password.encode("utf-8")):
            raise HTTPException(422, "現在とは異なるパスワードを入力してください。")
        validate_new_password(new_password, before["username"])
        salt = secrets.token_hex(16)
        encoded = password_hash(new_password, salt)
        with self.db.transaction(True) as conn:
            # Logout, expiry, a concurrent password change, or account disabling
            # during hashing must win. Both statements are fixed literals.
            session_query = (
                "SELECT u.username,u.salt,u.password_hash,u.login_enabled,s.csrf_token "
                "FROM stage_sessions s JOIN users u ON u.id=s.user_id "
                "WHERE s.token_hash=? AND s.user_id=? AND s.expires_at>?"
            ) if stage else (
                "SELECT u.username,u.salt,u.password_hash,u.login_enabled,s.csrf_token "
                "FROM sessions s JOIN users u ON u.id=s.user_id "
                "WHERE s.token_hash=? AND s.user_id=? AND s.expires_at>?"
            )
            fresh = conn.execute(
                session_query,
                (session["token_hash"], user_id, now()),
            ).fetchone()
            if (fresh is None or not fresh["login_enabled"]
                    or fresh["salt"] != before["salt"]
                    or fresh["password_hash"] != before["password_hash"]
                    or fresh["username"] != before["username"]
                    or not secrets.compare_digest(fresh["csrf_token"], session["csrf_token"])):
                raise HTTPException(401, "接続が切り替わりました。もう一度ログインしてください。")
            conn.execute("UPDATE users SET salt=?,password_hash=? WHERE id=?", (salt, encoded, user_id))
            conn.execute("DELETE FROM sessions WHERE user_id=?", (user_id,))
            conn.execute("DELETE FROM stage_sessions WHERE user_id=?", (user_id,))
        return PasswordChanged()
