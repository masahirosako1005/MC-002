from datetime import datetime, timedelta, timezone
import hashlib
import json
import secrets
import threading

from fastapi import HTTPException

from .database import ACCOUNTS, TAGS, TRIPS, digest, identifier, now, password_hash
from .images import sanitize_image

COVER_KEYS = ("woodland", "coffee", "coast", "table")
TRIP_BY_ID = {trip["id"]: {**trip, "cover_key": {"mountain": "woodland", "coast": "coast", "cafe": "coffee", "games": "table"}[trip["cover_key"]]} for trip in TRIPS}


def require(row, message="記録が見つかりません。"):
    if row is None:
        raise HTTPException(404, message)
    return row


def user_out(row):
    return {"id": row["user_id"] if "user_id" in row.keys() else row["id"], **{key: row[key] for key in ("username", "name", "initials", "color")}}


def member(conn, uid, cid):
    return require(conn.execute("SELECT * FROM memberships WHERE user_id=? AND community_id=? AND status='active'", (uid, cid)).fetchone(), "コミュニティに参加している人だけが利用できます。")


def invalidate(conn, uid, cid=None):
    conn.execute("UPDATE proposals SET status='invalidated',version=version+1 WHERE status='pending' AND id IN (SELECT proposal_id FROM responses WHERE user_id=?)" + (" AND community_id=?" if cid else ""), (uid, cid) if cid else (uid,))


class Service:
    def __init__(self, database, settings, classifier):
        self.db, self.settings, self.classifier = database, settings, classifier
        self.decode_lock = threading.BoundedSemaphore(1)

    def login(self, username, password, previous_hash=None):
        with self.db.transaction(True) as conn:
            row = conn.execute("SELECT * FROM users WHERE username=? AND login_enabled=1", (username,)).fetchone()
            supplied = password_hash(password, row["salt"] if row else "0" * 32)
            if row is None or not secrets.compare_digest(supplied, row["password_hash"]):
                raise HTTPException(401, "利用者名かパスワードを確認してください。")
            if previous_hash:
                conn.execute("DELETE FROM sessions WHERE token_hash=?", (previous_hash,))
            conn.execute("DELETE FROM sessions WHERE expires_at<=?", (now(),))
            token, csrf = secrets.token_urlsafe(32), secrets.token_urlsafe(32)
            conn.execute("INSERT INTO sessions VALUES(?,?,?,?)", (digest(token), row["id"], csrf, (datetime.now(timezone.utc) + timedelta(days=30)).isoformat()))
            return {"user": user_out(row), "csrf_token": csrf}, token

    def community_out(self, conn, cid, uid):
        membership = member(conn, uid, cid)
        row = require(conn.execute("SELECT * FROM communities WHERE id=?", (cid,)).fetchone())
        return {"id": cid, "name": row["name"], "description": row["description"], "cover_key": {"mountain": "woodland", "coast": "coast"}.get(row["cover_key"], row["cover_key"]),
                "role": membership["role"], "member_count": conn.execute("SELECT COUNT(*) FROM memberships WHERE community_id=? AND status='active'", (cid,)).fetchone()[0]}

    def communities(self, uid):
        with self.db.transaction() as conn:
            return {"items": [self.community_out(conn, row[0], uid) for row in conn.execute("SELECT community_id FROM memberships WHERE user_id=? AND status='active' ORDER BY community_id DESC", (uid,))]}

    def community(self, uid, cid):
        with self.db.transaction() as conn:
            result = self.community_out(conn, cid, uid)
            return {"community": result, "invite_code": conn.execute("SELECT invite_code FROM communities WHERE id=?", (cid,)).fetchone()[0] if result["role"] == "owner" else None}

    def create_community(self, uid, data):
        cid, invite = identifier(), secrets.token_urlsafe(18)
        with self.db.transaction(True) as conn:
            conn.execute("INSERT INTO communities VALUES(?,?,?,?,?,'woodland')", (cid, data["name"], data["description"], digest(invite), invite))
            conn.execute("INSERT INTO memberships VALUES(?,?,'owner','active')", (cid, uid))
            conn.execute("INSERT INTO grants VALUES(?,?,0,0,0)", (uid, cid))
            return self.community_out(conn, cid, uid)

    def join(self, uid, code):
        with self.db.transaction(True) as conn:
            row = require(conn.execute("SELECT id FROM communities WHERE invite_hash=?", (digest(code),)).fetchone(), "招待コードを確認してください。")
            cid = row["id"]
            conn.execute("INSERT INTO memberships VALUES(?,?,'member','active') ON CONFLICT(community_id,user_id) DO UPDATE SET status='active'", (cid, uid))
            conn.execute("INSERT OR IGNORE INTO grants VALUES(?,?,0,0,0)", (uid, cid))
            return self.community_out(conn, cid, uid)

    def leave(self, uid, cid):
        with self.db.transaction(True) as conn:
            membership = member(conn, uid, cid)
            if membership["role"] == "owner" and conn.execute("SELECT COUNT(*) FROM memberships WHERE community_id=? AND status='active'", (cid,)).fetchone()[0] > 1:
                raise HTTPException(409, "管理者は他の参加者がいる間は退会できません。")
            conn.execute("UPDATE memberships SET status='left' WHERE community_id=? AND user_id=?", (cid, uid))
            conn.execute("UPDATE grants SET use_matching=0,display_matching=0,participate=0 WHERE community_id=? AND user_id=?", (cid, uid))
            conn.execute("UPDATE posts SET status='draft' WHERE community_id=? AND user_id=? AND status='published'", (cid, uid))
            invalidate(conn, uid, cid)
            return {"ok": True}

    @staticmethod
    def analysis_out(conn, mid):
        row = require(conn.execute("SELECT * FROM jobs WHERE media_id=?", (mid,)).fetchone())
        return {"status": row["status"], "tags": json.loads(row["tags"]), "message": row["message"], "model_version": row["model_version"]}

    def media_out(self, conn, row):
        return {"id": row["id"], "url": "/api/media/" + row["id"], "width": row["width"], "height": row["height"], "analysis": self.analysis_out(conn, row["id"])}

    def upload(self, uid, raw):
        if not self.decode_lock.acquire(blocking=False):
            raise HTTPException(429, "写真を処理しています。少し待って再送してください。")
        try:
            clean, width, height = sanitize_image(raw, self.settings)
        finally:
            self.decode_lock.release()
        mid = identifier()
        key = mid + ".jpg"
        destination = self.settings.media_dir / key
        try:
            with self.db.transaction(True) as conn:
                if conn.execute("SELECT COUNT(*) FROM media WHERE user_id=? AND deleted=0", (uid,)).fetchone()[0] >= 200:
                    raise HTTPException(409, "保存枚数の上限です。不要な投稿を削除してください。")
                destination.write_bytes(clean)
                conn.execute("INSERT INTO media(id,user_id,storage_key,width,height,sha256,created_at) VALUES(?,?,?,?,?,?,?)", (mid, uid, key, width, height, hashlib.sha256(clean).hexdigest(), now()))
                conn.execute("INSERT INTO jobs(media_id,status,message) VALUES(?,'queued','写真を確認しています。タグはあとで直せます。')", (mid,))
                return self.media_out(conn, conn.execute("SELECT * FROM media WHERE id=?", (mid,)).fetchone())
        except BaseException:
            destination.unlink(missing_ok=True)
            raise

    def media_path(self, uid, mid):
        with self.db.transaction() as conn:
            row = require(conn.execute("SELECT * FROM media WHERE id=? AND deleted=0", (mid,)).fetchone())
            if row["user_id"] != uid:
                allowed = conn.execute("SELECT 1 FROM post_media pm JOIN posts p ON p.id=pm.post_id JOIN memberships m ON m.community_id=p.community_id WHERE pm.media_id=? AND p.status='published' AND m.user_id=? AND m.status='active'", (mid, uid)).fetchone()
                require(allowed)
            return self.settings.media_dir / row["storage_key"]

    def analysis(self, uid, mid, retry=False):
        with self.db.transaction(retry) as conn:
            require(conn.execute("SELECT 1 FROM media WHERE id=? AND user_id=? AND deleted=0", (mid, uid)).fetchone())
            if retry:
                conn.execute("UPDATE jobs SET status='queued',attempts=0,message='写真を確認しています。',tags='[]' WHERE media_id=? AND status NOT IN ('queued','running')", (mid,))
            return self.analysis_out(conn, mid)

    def post_out(self, conn, row, uid):
        media = [self.media_out(conn, image) for image in conn.execute("SELECT m.* FROM media m JOIN post_media pm ON pm.media_id=m.id WHERE pm.post_id=? AND m.deleted=0 ORDER BY pm.position", (row["id"],))]
        author = conn.execute("SELECT * FROM users WHERE id=?", (row["user_id"],)).fetchone()
        # Other members see the chosen tags, not private analysis candidates.
        if row["user_id"] != uid:
            for image in media:
                image["analysis"] = {"status": image["analysis"]["status"], "tags": [], "message": "投稿者が選んだタグを表示しています。", "model_version": None}
        return {"id": row["id"], "community_id": row["community_id"], "author": user_out(author), "body": row["body"], "tags": json.loads(row["tags"]), "media": media,
                "status": row["status"], "created_at": row["created_at"], "place_label": row["place_label"], "taken_on": row["taken_on"], "can_edit": row["user_id"] == uid}

    def feed(self, uid, cid):
        with self.db.transaction() as conn:
            member(conn, uid, cid)
            return {"items": [self.post_out(conn, row, uid) for row in conn.execute("SELECT * FROM posts WHERE community_id=? AND (status='published' OR (status='draft' AND user_id=?)) ORDER BY created_at DESC,id LIMIT 100", (cid, uid))]}

    def create_post(self, uid, data):
        if len(data["media_ids"]) != len(set(data["media_ids"])):
            raise HTTPException(422, "同じ写真を重ねて選べません。")
        with self.db.transaction(True) as conn:
            member(conn, uid, data["community_id"])
            for mid in data["media_ids"]:
                require(conn.execute("SELECT 1 FROM media WHERE id=? AND user_id=? AND deleted=0", (mid, uid)).fetchone())
                if conn.execute("SELECT 1 FROM post_media WHERE media_id=?", (mid,)).fetchone():
                    raise HTTPException(409, "この写真はすでに投稿に追加されています。")
            pid = identifier()
            conn.execute("INSERT INTO posts VALUES(?,?,?,?,?,'draft',?,?,?)", (pid, uid, data["community_id"], data["body"], json.dumps(data["tags"]), data["place_label"], data["taken_on"], now()))
            conn.executemany("INSERT INTO post_media VALUES(?,?,?)", [(pid, mid, position) for position, mid in enumerate(data["media_ids"])])
            return self.post_out(conn, conn.execute("SELECT * FROM posts WHERE id=?", (pid,)).fetchone(), uid)

    def patch_post(self, uid, pid, data):
        with self.db.transaction(True) as conn:
            row = require(conn.execute("SELECT * FROM posts WHERE id=? AND user_id=? AND status!='deleted'", (pid, uid)).fetchone())
            member(conn, uid, row["community_id"])
            values = dict(row)
            for key in ("body", "status", "place_label", "taken_on"):
                if key in data:
                    values[key] = data[key]
            if data.get("tags") is not None:
                values["tags"] = json.dumps(data["tags"])
            if any(values[key] is None for key in ("body", "status", "place_label")):
                raise HTTPException(422, "入力を確認してください。")
            conn.execute("UPDATE posts SET body=?,tags=?,status=?,place_label=?,taken_on=? WHERE id=?", (values["body"], values["tags"], values["status"], values["place_label"], values["taken_on"], pid))
            invalidate(conn, uid)
            return self.post_out(conn, conn.execute("SELECT * FROM posts WHERE id=?", (pid,)).fetchone(), uid)

    def delete_post(self, uid, pid):
        paths = []
        with self.db.transaction(True) as conn:
            require(conn.execute("SELECT 1 FROM posts WHERE id=? AND user_id=?", (pid, uid)).fetchone())
            for row in conn.execute("SELECT m.* FROM media m JOIN post_media pm ON pm.media_id=m.id WHERE pm.post_id=?", (pid,)):
                conn.execute("UPDATE media SET deleted=1 WHERE id=?", (row["id"],))
                conn.execute("UPDATE jobs SET status='failed',tags='[]',message='写真は削除されました。' WHERE media_id=?", (row["id"],))
                paths.append(self.settings.media_dir / row["storage_key"])
            conn.execute("UPDATE posts SET status='deleted',body='',tags='[]',place_label='',taken_on=NULL WHERE id=?", (pid,))
            invalidate(conn, uid)
        for path in paths:
            try:
                path.unlink(missing_ok=True)
            except OSError:
                pass  # Access is already denied; worker cleanup retries removal.
        return {"ok": True}

    def preference_out(self, conn, uid):
        row = require(conn.execute("SELECT * FROM preferences WHERE user_id=?", (uid,)).fetchone())
        evidence = []
        if row["learn_from_posts"]:
            for post in conn.execute("SELECT id,tags FROM posts WHERE user_id=? AND status='published'", (uid,)):
                evidence.extend({"tag_id": tag, "post_id": post["id"]} for tag in json.loads(post["tags"]))
        # Only manually confirmed portable tags are used for cross-group matching.
        return {"tags": json.loads(row["tags"]), "learn_from_posts": bool(row["learn_from_posts"]), "evidence": evidence,
                "grants": [{"community_id": grant["community_id"], "use_for_matching": bool(grant["use_matching"]), "display_in_matches": bool(grant["display_matching"]), "participate": bool(grant["participate"])} for grant in conn.execute("SELECT g.* FROM grants g JOIN memberships m ON m.community_id=g.community_id AND m.user_id=g.user_id WHERE g.user_id=? AND m.status='active'", (uid,))]}

    def preferences(self, uid, data=None):
        with self.db.transaction(data is not None) as conn:
            if data is not None:
                communities = [grant["community_id"] for grant in data["grants"]]
                if len(communities) != len(set(communities)):
                    raise HTTPException(422, "コミュニティが重複しています。")
                for grant in data["grants"]:
                    member(conn, uid, grant["community_id"])
                conn.execute("UPDATE preferences SET tags=?,learn_from_posts=?,version=version+1 WHERE user_id=?", (json.dumps(data["tags"]), int(data["learn_from_posts"]), uid))
                conn.execute("UPDATE grants SET use_matching=0,display_matching=0,participate=0 WHERE user_id=?", (uid,))
                for grant in data["grants"]:
                    conn.execute("INSERT INTO grants VALUES(?,?,?,?,?) ON CONFLICT(user_id,community_id) DO UPDATE SET use_matching=excluded.use_matching,display_matching=excluded.display_matching,participate=excluded.participate", (uid, grant["community_id"], int(grant["use_for_matching"]), int(grant["display_in_matches"]), int(grant["participate"])))
                invalidate(conn, uid)
            return self.preference_out(conn, uid)

    def proposal_out(self, conn, row, uid):
        member(conn, uid, row["community_id"])
        own = require(conn.execute("SELECT decision FROM responses WHERE proposal_id=? AND user_id=?", (row["id"], uid)).fetchone())
        participants = []
        for response in conn.execute("SELECT r.decision,u.*,m.status AS membership_status,g.use_matching,g.display_matching,g.participate,p.tags FROM responses r JOIN users u ON u.id=r.user_id JOIN memberships m ON m.user_id=u.id AND m.community_id=? JOIN grants g ON g.user_id=u.id AND g.community_id=m.community_id JOIN preferences p ON p.user_id=u.id WHERE r.proposal_id=? ORDER BY u.login_enabled DESC,u.id", (row["community_id"], row["id"])):
            if response["membership_status"] != "active" or not all(response[key] for key in ("use_matching", "display_matching", "participate")):
                continue
            participants.append({"id": response["id"], "name": response["name"], "initials": response["initials"], "color": response["color"],
                                 "common_tags": sorted(set(json.loads(response["tags"])) & set(json.loads(row["tags"]))),
                                 "response": "unavailable" if row["status"] == "invalidated" else response["decision"]})
        return {"id": row["id"], "community_id": row["community_id"], "purpose": row["purpose"], "date": row["date"], "trip": TRIP_BY_ID[row["trip_id"]], "participants": participants, "my_response": own["decision"],
                "status": row["status"], "version": row["version"], "group_id": row["group_id"], "reason": "本人が許可した関心が共通しています。参加は一人ずつ確認します。" if row["status"] != "invalidated" else "参加条件が変わりました。新しい提案を作ってください。", "created_at": row["created_at"]}

    def propose(self, uid, cid, data):
        if data["trip_id"] not in TRIP_BY_ID:
            raise HTTPException(422, "旅の候補を選んでください。")
        if not set(data["tags"]) & set(TRIP_BY_ID[data["trip_id"]]["tags"]):
            raise HTTPException(409, "選んだ関心に合う旅の候補を選んでください。")
        with self.db.transaction(True) as conn:
            member(conn, uid, cid)
            rows = conn.execute("SELECT u.*,p.tags FROM memberships m JOIN users u ON u.id=m.user_id JOIN preferences p ON p.user_id=u.id JOIN grants g ON g.user_id=u.id AND g.community_id=m.community_id WHERE m.community_id=? AND m.status='active' AND g.use_matching=1 AND g.display_matching=1 AND g.participate=1", (cid,)).fetchall()
            eligible = [(len(set(json.loads(row["tags"])) & set(data["tags"])), row) for row in rows]
            eligible = [(score, row) for score, row in eligible if score > 0]
            if not any(row["id"] == uid for _, row in eligible):
                raise HTTPException(409, "自分の好みと、このコミュニティでの利用・表示・参加許可を確認してください。")
            eligible.sort(key=lambda item: (-item[0], item[1]["id"]))
            candidates = [uid] + [row["id"] for _, row in eligible if row["id"] != uid][:data["size"] - 1]
            if len(candidates) < data["size"]:
                raise HTTPException(409, "条件と許可を満たす人数が足りません。人数や希望を見直してください。")
            pid = identifier()
            conn.execute("INSERT INTO proposals(id,community_id,created_by,purpose,trip_id,tags,date,status,created_at) VALUES(?,?,?,?,?,?,?,'pending',?)", (pid, cid, uid, data["purpose"], data["trip_id"], json.dumps(data["tags"]), data["date"], now()))
            conn.executemany("INSERT INTO responses(proposal_id,user_id) VALUES(?,?)", [(pid, person) for person in candidates])
            return self.proposal_out(conn, conn.execute("SELECT * FROM proposals WHERE id=?", (pid,)).fetchone(), uid)

    def proposals(self, uid, pid=None):
        with self.db.transaction() as conn:
            if pid:
                return self.proposal_out(conn, require(conn.execute("SELECT * FROM proposals WHERE id=?", (pid,)).fetchone()), uid)
            rows = conn.execute("SELECT p.* FROM proposals p JOIN responses r ON r.proposal_id=p.id JOIN memberships m ON m.community_id=p.community_id AND m.user_id=r.user_id WHERE r.user_id=? AND m.status='active' ORDER BY p.created_at DESC LIMIT 50", (uid,))
            return {"items": [self.proposal_out(conn, row, uid) for row in rows]}

    def respond(self, uid, pid, data):
        with self.db.transaction(True) as conn:
            row = require(conn.execute("SELECT * FROM proposals WHERE id=?", (pid,)).fetchone())
            member(conn, uid, row["community_id"])
            own = require(conn.execute("SELECT decision FROM responses WHERE proposal_id=? AND user_id=?", (pid, uid)).fetchone())
            if own["decision"] == data["decision"]:
                return self.proposal_out(conn, row, uid)
            if row["status"] != "pending" or row["version"] != data["version"]:
                raise HTTPException(409, "提案が更新されています。内容を開き直してください。")
            valid = conn.execute("SELECT COUNT(*) FROM responses r JOIN memberships m ON m.user_id=r.user_id AND m.community_id=? JOIN grants g ON g.user_id=r.user_id AND g.community_id=m.community_id WHERE r.proposal_id=? AND m.status='active' AND g.use_matching=1 AND g.display_matching=1 AND g.participate=1", (row["community_id"], pid)).fetchone()[0]
            total = conn.execute("SELECT COUNT(*) FROM responses WHERE proposal_id=?", (pid,)).fetchone()[0]
            if valid != total:
                raise HTTPException(409, "参加条件が変わりました。新しい提案を作ってください。")
            conn.execute("UPDATE responses SET decision=? WHERE proposal_id=? AND user_id=?", (data["decision"], pid, uid))
            status, gid = "pending", None
            if data["decision"] == "declined":
                status = "invalidated"
            elif conn.execute("SELECT COUNT(*) FROM responses WHERE proposal_id=? AND decision='accepted'", (pid,)).fetchone()[0] == total:
                status, gid = "formed", identifier()
                conn.execute("INSERT INTO ko_groups(id,proposal_id,community_id,purpose,trip_id,date,created_at) VALUES(?,?,?,?,?,?,?)", (gid, pid, row["community_id"], row["purpose"], row["trip_id"], row["date"], now()))
                conn.execute("INSERT INTO group_members(group_id,user_id) SELECT ?,user_id FROM responses WHERE proposal_id=?", (gid, pid))
            conn.execute("UPDATE proposals SET status=?,group_id=?,version=version+1 WHERE id=?", (status, gid, pid))
            return self.proposal_out(conn, conn.execute("SELECT * FROM proposals WHERE id=?", (pid,)).fetchone(), uid)

    def group_out(self, conn, row, uid):
        member(conn, uid, row["community_id"])
        require(conn.execute("SELECT 1 FROM group_members WHERE group_id=? AND user_id=?", (row["id"], uid)).fetchone())
        people = conn.execute("SELECT u.*,g.role,g.note FROM group_members g JOIN users u ON u.id=g.user_id JOIN memberships m ON m.user_id=u.id AND m.community_id=? WHERE g.group_id=? AND m.status='active' ORDER BY u.id", (row["community_id"], row["id"])).fetchall()
        return {"id": row["id"], "community_id": row["community_id"], "purpose": row["purpose"], "trip": TRIP_BY_ID[row["trip_id"]], "members": [user_out(person) for person in people],
                "contributions": [{"user_id": person["id"], "name": person["name"], "role": person["role"], "note": person["note"]} for person in people],
                "plan": {"date": row["date"], "meeting_point": row["meeting_point"], "notes": row["notes"], "version": row["version"]}, "created_at": row["created_at"]}

    def groups(self, uid, gid=None):
        with self.db.transaction() as conn:
            if gid:
                return self.group_out(conn, require(conn.execute("SELECT * FROM ko_groups WHERE id=?", (gid,)).fetchone()), uid)
            rows = conn.execute("SELECT k.* FROM ko_groups k JOIN group_members g ON g.group_id=k.id JOIN memberships m ON m.community_id=k.community_id AND m.user_id=g.user_id WHERE g.user_id=? AND m.status='active' ORDER BY k.created_at DESC", (uid,))
            return {"items": [self.group_out(conn, row, uid) for row in rows]}

    def update_group(self, uid, gid, data, contribution=False):
        with self.db.transaction(True) as conn:
            row = require(conn.execute("SELECT * FROM ko_groups WHERE id=?", (gid,)).fetchone())
            self.group_out(conn, row, uid)
            if contribution:
                conn.execute("UPDATE group_members SET role=?,note=? WHERE group_id=? AND user_id=?", (data["role"], data["note"], gid, uid))
            else:
                if row["version"] != data["version"]:
                    raise HTTPException(409, "計画が更新されています。開き直してください。")
                conn.execute("UPDATE ko_groups SET date=?,meeting_point=?,notes=?,version=version+1 WHERE id=?", (data["date"], data["meeting_point"], data["notes"], gid))
            return self.group_out(conn, conn.execute("SELECT * FROM ko_groups WHERE id=?", (gid,)).fetchone(), uid)

    def seed_assets(self):
        folder = self.settings.seed_asset_dir
        if folder is None or not folder.is_dir():
            return
        cover_dir = self.settings.media_dir / "covers"
        cover_dir.mkdir(exist_ok=True)
        for key in COVER_KEYS:
            source = folder / (key + ".png")
            if source.is_file() and not (cover_dir / (key + ".jpg")).exists():
                clean, _, _ = sanitize_image(source.read_bytes(), self.settings)
                (cover_dir / (key + ".jpg")).write_bytes(clean)
        with self.db.transaction() as conn:
            if conn.execute("SELECT 1 FROM settings WHERE key='seed-assets'").fetchone():
                return
        for key, uid, cid, tags, caption in [
            ("woodland", "u-aoi", "campus", ["mountain", "nature", "cafe"], "木立の向こうまで歩いた日。次は喫茶店にも寄りたい。"),
            ("coffee", "u-mio", "peers", ["cafe", "food"], "散歩の途中のひと休み。気になるお店を持ち寄りたい。"),
            ("coast", "u-ren", "peers", ["coast", "walk"], "波の音を聞きながら、浜をゆっくり歩く。"),
            ("table", "u-aoi", "peers", ["food", "games", "stay"], "旅の終わりにテーブルを囲む時間も好き。"),
        ]:
            source = folder / (key + ".png")
            if not source.is_file():
                continue
            image = self.upload(uid, source.read_bytes())
            post = self.create_post(uid, {"community_id": cid, "body": caption, "media_ids": [image["id"]], "tags": tags, "place_label": "", "taken_on": None})
            self.patch_post(uid, post["id"], {"status": "published"})
        with self.db.transaction(True) as conn:
            conn.execute("INSERT OR IGNORE INTO settings VALUES('seed-assets','1')")
