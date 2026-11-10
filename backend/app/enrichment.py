"""Explicit, additive fictional content pack; never part of normal startup.

No survey rows are copied. Fixed IDs and a committed manifest make the import
idempotent. Existing rows and user credentials are never updated or replaced.
"""
import argparse
import hashlib
import json
import secrets
from datetime import UTC, datetime, timedelta

from .config import Settings
from .database import Database, password_hash
from .daytrip.catalog import ROUTES
from .images import sanitize_image
from .marketplace.service import Marketplace, dump

PACK = "content-20261110-v1"
PREFIX = "extra26-"
NAMES = (
    "佐藤 夏希", "山口 航", "田中 美咲", "石井 拓海", "中村 彩", "森 悠人",
    "清水 遥", "山本 慎", "小林 紬", "松本 陸", "吉田 明里", "池田 圭",
    "井上 楓", "木村 直人", "橋本 花", "鈴木 颯", "岡田 真央", "藤田 樹",
    "林 千尋", "伊藤 翔", "山田 咲", "渡辺 律", "小川 杏", "加藤 仁",
    "斎藤 凛", "石川 湊", "前田 美月", "村上 晃", "長谷川 結", "阿部 蒼",
    "近藤 春", "遠藤 諒", "青木 菫", "坂本 晴", "西村 翠", "福田 岳",
)
TOPICS = (
    ("公園と喫茶店", ["walk", "cafe", "nature"], "coffee", "N西市・門前町", "公園の木陰を歩いて、駅前でコーヒー。午前の散策なら人も少なく、ゆっくり話せました。"),
    ("里山を歩く", ["mountain", "nature", "walk"], "woodland", "N西市・北山", "歩きやすい靴で里山へ。坂道の後はベンチで休憩して、お弁当を囲みました。"),
    ("川辺と食堂", ["coast", "food", "walk"], "coast", "N西市・川辺", "川沿いを一周してからまちの食堂へ。午後は風が強くなるので、散歩は午前がおすすめです。"),
    ("食事とボードゲーム", ["games", "food", "cafe"], "table", "N西市・門前町", "散歩の後に集まってボードゲーム。初めての人にも遊び方を教え合い、夕方まで楽しめました。"),
    ("小さな店をめぐる", ["fashion", "walk", "cafe"], "coffee", "N西市・門前町", "商店街で器と小物を見てきました。気になったお店をそれぞれ一つずつ案内しました。"),
    ("自然観察の休日", ["nature", "mountain", "food"], "woodland", "N西市・北山", "植物を見ながらゆっくり散策。帰りの時間を先に決めておいたので、日帰りでも落ち着いて過ごせました。"),
)

INSERT_SQL = {
    "users": "INSERT INTO users(id,username,name,initials,color,salt,password_hash,login_enabled) VALUES(?,?,?,?,?,?,?,?)",
    "residence_profiles": "INSERT INTO residence_profiles(user_id,area_id,share_analytics,version,updated_at) VALUES(?,?,?,?,?)",
    "preferences": "INSERT INTO preferences(user_id,tags,learn_from_posts) VALUES(?,?,?)",
    "memberships": "INSERT INTO memberships(community_id,user_id,role,status) VALUES(?,?,?,?)",
    "grants": "INSERT INTO grants(user_id,community_id,use_matching,display_matching,participate) VALUES(?,?,?,?,?)",
    "provider_plans": "INSERT INTO provider_plans(id,provider_id,body,status,version,updated_at) VALUES(?,?,?,?,?,?)",
    "daytrip_plan_routes": "INSERT INTO daytrip_plan_routes(plan_id,route_id,updated_by,updated_at) VALUES(?,?,?,?)",
    "posts": "INSERT INTO posts(id,user_id,community_id,body,tags,status,place_label,taken_on,created_at) VALUES(?,?,?,?,?,?,?,?,?)",
    "media": "INSERT INTO media(id,user_id,storage_key,width,height,sha256,created_at) VALUES(?,?,?,?,?,?,?)",
    "jobs": "INSERT INTO jobs(media_id,status,tags,message) VALUES(?,?,?,?)",
    "post_media": "INSERT INTO post_media(post_id,media_id,position) VALUES(?,?,?)",
    "travel_parties": "INSERT INTO travel_parties(id,community_id,ko_group_id,representative_id,title,status,created_at) VALUES(?,?,?,?,?,?,?)",
    "circle_rooms": "INSERT INTO circle_rooms(party_id,mode,desired_count,tags,created_at) VALUES(?,?,?,?,?)",
    "travel_party_members": "INSERT INTO travel_party_members(party_id,user_id) VALUES(?,?)",
    "travel_requirements": "INSERT INTO travel_requirements(party_id,body,version,confirmed_by,confirmed_at) VALUES(?,?,?,?,?)",
    "plan_selections": "INSERT INTO plan_selections(id,party_id,plan_id,provider_id,snapshot,selected_by,status,created_at) VALUES(?,?,?,?,?,?,?,?)",
    "consultations": "INSERT INTO consultations(id,selection_id,status,created_at) VALUES(?,?,?,?)",
    "circle_provider_invitations": "INSERT INTO circle_provider_invitations(id,party_id,provider_id,inviter_id,snapshot,status,consultation_id,created_at,accepted_at) VALUES(?,?,?,?,?,?,?,?,?)",
    "consultation_messages": "INSERT INTO consultation_messages(id,consultation_id,author_id,body,created_at) VALUES(?,?,?,?,?)",
    "party_messages": "INSERT INTO party_messages(id,party_id,author_id,body,created_at) VALUES(?,?,?,?,?)",
    "daytrip_outings": "INSERT INTO daytrip_outings(id,circle_id,title,route_json,starts_at,ends_at,day,status,leader_id,leader_accepted,plan_id,provider_id,invitation_id,plan_json,created_by,created_at) VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)",
    "daytrip_participants": "INSERT INTO daytrip_participants(outing_id,user_id,accepted,claimed,full_route,confirmed_by,provider_verified,points,revoked) VALUES(?,?,?,?,?,?,?,?,?)",
    "daytrip_daily_awards": "INSERT INTO daytrip_daily_awards(user_id,day,outing_id) VALUES(?,?,?)",
    "daytrip_ledger": "INSERT INTO daytrip_ledger(id,outing_id,user_id,kind,points,eligible_points,reason,rule_version,created_at) VALUES(?,?,?,?,?,?,?,?,?)",
    "daytrip_benefits": "INSERT INTO daytrip_benefits(id,provider_id,plan_id,title,min_rank,discount_type,discount_value,max_discount_yen,max_redemptions,starts_on,ends_on,status,created_at) VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?)",
    "settings": "INSERT INTO settings(key,value) VALUES(?,?)",
}


def key(kind, index):
    return f"{PREFIX}{kind}-{index:03}"


def stamp(base, days, hour=1):
    return (base - timedelta(days=days)).replace(hour=hour, minute=0, second=0, microsecond=0).isoformat()


def insert(conn, table, values):
    query = INSERT_SQL[table]
    columns = query.split("(", 1)[1].split(")", 1)[0].split(",")
    if set(columns) != values.keys():
        raise ValueError("Unexpected enrichment columns")
    conn.execute(query, tuple(values[column] for column in columns))


def seed_people(conn, base):
    for index, name in enumerate(NAMES):
        uid = key("person", index)
        salt = secrets.token_hex(16)
        # These fictional profiles are not extra public login accounts.
        insert(conn, "users", dict(id=uid, username=uid, name=name, initials=name.split()[-1][:1],
            color=["#835340", "#566B59", "#746247"][index % 3], salt=salt,
            password_hash=password_hash(secrets.token_urlsafe(32), salt), login_enabled=1))
        insert(conn, "residence_profiles", dict(user_id=uid, area_id=("27100","27140","26100","28100","29201","27205")[index // 6], share_analytics=1, version=1, updated_at=base.isoformat()))
        insert(conn, "preferences", dict(user_id=uid, tags=dump(TOPICS[index % 6][1]), learn_from_posts=0))
        insert(conn, "memberships", dict(community_id="peers", user_id=uid, role="member", status="active"))
        insert(conn, "grants", dict(user_id=uid, community_id="peers", use_matching=1, display_matching=1, participate=1))


def seed_plans(conn, base):
    for index in range(12):
        topic, tags, _, area, _ = TOPICS[index % 6]
        provider = "shore-school" if index % 6 == 2 else "forest-house"
        night = 1 if index in (8, 11) else 0
        body = dict(title=f"{area}で{topic}" + ("・宿泊" if night else "・日帰り") + ("（団体向け）" if index >= 6 else ""),
            summary="午前の集合から帰着まで、人数と歩く距離に合わせて相談できます。",
            area=area, min_people=2, max_people=40 if index >= 6 else 8, nights=night,
            price_yen=4200 + index * 600 + night * 9000, price_basis="per_person", price_scope="plan_only",
            price_note="体験と食事の料金。往復の交通費は含みません。営業日と受入人数は相談で確認します。",
            tags=tags, itinerary=[dict(day=day + 1, period="morning", place=area + "の集合場所",
                description=topic + "を楽しんでから、夕方に解散します。", travel_minutes=20) for day in range(night + 1)],
            schedule_type="on_request", starts_at=None, ends_at=None)
        # Four real selectable dated entries; the others remain request-based.
        if index in (3, 5, 7, 9):
            body.update(schedule_type="dated", starts_at=stamp(base, -7-index), ends_at=stamp(base, -7-index, 8))
        insert(conn, "provider_plans", dict(id=key("plan", index), provider_id=provider, body=dump(body),
            status="published", version=1, updated_at=base.isoformat()))
        if not night and area in ("N西市・門前町", "N西市・北山"):
            route = ROUTES[0 if area == "N西市・門前町" else 1]
            insert(conn, "daytrip_plan_routes", dict(plan_id=key("plan", index), route_id=route["id"],
                updated_by="provider-forest", updated_at=base.isoformat()))


def seed_posts(conn, settings, base):
    photos = 0
    for index in range(48):
        _, tags, cover, area, caption = TOPICS[index % 6]
        uid, pid = key("person", index % 36), key("post", index)
        created = stamp(base, index * 2 + 1, 9)
        insert(conn, "posts", dict(id=pid, user_id=uid, community_id="peers", body=f"{caption}\n今回は{2 + index % 5}人で出かけました。", tags=dump(tags),
            status="published", place_label=area, taken_on=created[:10], created_at=created))
        if index % 4 >= 2 or not settings.seed_asset_dir:
            continue
        source = settings.seed_asset_dir / (cover + ".png")
        if not source.is_file():
            continue
        clean, width, height = sanitize_image(source.read_bytes(), settings)
        mid = key("media", index)
        path = settings.media_dir / (mid + ".jpg")
        # A file left by an interrupted uncommitted import is safe to reuse only
        # if its sanitized bytes are identical. Never replace any other content.
        if path.exists() and path.read_bytes() != clean:
            raise ValueError("Enrichment media ID collision")
        if not path.exists():
            path.write_bytes(clean)
        insert(conn, "media", dict(id=mid, user_id=uid, storage_key=path.name, width=width, height=height,
            sha256=hashlib.sha256(clean).hexdigest(), created_at=created))
        insert(conn, "jobs", dict(media_id=mid, status="manual", tags="[]", message="投稿者がタグを選びました。"))
        insert(conn, "post_media", dict(post_id=pid, media_id=mid, position=0))
        photos += 1
    return photos


def seed_benefits(conn, base):
    for index, (plan_index, rank, rate) in enumerate(((0, 2, 5), (1, 3, 5), (6, 4, 8), (10, 5, 10))):
        bid = key('benefit', index)
        insert(conn, 'daytrip_benefits', dict(id=bid, provider_id='forest-house', plan_id=key('plan', plan_index),
            title=TOPICS[plan_index % 6][0] + 'の参加特典', min_rank=rank, discount_type='percent',
            discount_value=rate, max_discount_yen=800, max_redemptions=100,
            starts_on=base.date().isoformat(), ends_on=(base+timedelta(days=180)).date().isoformat(),
            status='published', created_at=base.isoformat()))
        insert(conn, 'settings', dict(key='daytrip-benefit-rank:' + bid, value='R2'))


def seed_circle(conn, market, index, base):
    topic, tags, _, area, _ = TOPICS[index % 6]
    cid, sid, consult, invite = (key(kind, index) for kind in ("circle", "selection", "consult", "invite"))
    members = [key("person", (index + offset) % 36) for offset in range(4 + index % 3)]
    # Existing users can inspect six upcoming planning rooms, but no fabricated
    # earned points or confirmed visits are attached to their accounts.
    if index >= 36:
        members = ["u-aoi", "u-ren", "u-mio", *members[:3]]
    created = stamp(base, 9+index*2 if index < 36 else index-35)
    title = f"{area}・{topic}の講 {index + 1}"
    insert(conn, "travel_parties", dict(id=cid, community_id="peers", ko_group_id=None,
        representative_id=members[0], title=title, status="open", created_at=created))
    insert(conn, "circle_rooms", dict(party_id=cid, mode="manual", desired_count=len(members), tags=dump(tags), created_at=created))
    for uid in members:
        insert(conn, "travel_party_members", dict(party_id=cid, user_id=uid))
    # Use undated day plans for past records. Snapshot values reflect the
    # conversation's shared scope; individual interests remain private.
    plan_index = (0, 1, 2, 4, 6, 10)[index % 6]
    row = conn.execute("SELECT * FROM provider_plans WHERE id=?", (key("plan", plan_index),)).fetchone()
    plan = market.plan_out(conn, row)
    travel_day = (base - timedelta(days=2 + index * 2) if index < 36 else base + timedelta(days=index - 28)).date().isoformat()
    conditions = dict(planned_people=35 if index % 6 == 4 and plan["max_people"] >= 35 else len(members), nights=plan["nights"],
        budget_yen=plan["price_yen"] + 2000, budget_basis="per_person", budget_scope="plan_only", date_start=travel_day)
    req = {**conditions, "interests": tags, "departure_label": "大阪駅"}
    insert(conn, "travel_requirements", dict(party_id=cid, body=dump(req), version=1, confirmed_by=members[0], confirmed_at=created))
    snapshot = dict(plan=plan, shared_conditions=conditions, share_note="集合時間と歩く距離を相談したいです。",
        requirements_version=1, unknowns=["営業・空席は相談時に確認"])
    insert(conn, "plan_selections", dict(id=sid, party_id=cid, plan_id=plan["id"], provider_id=plan["provider"]["id"],
        snapshot=dump(snapshot), selected_by=members[0], status="active", created_at=created))
    insert(conn, "consultations", dict(id=consult, selection_id=sid, status="open", created_at=created))
    insert(conn, "circle_provider_invitations", dict(id=invite, party_id=cid, provider_id=plan["provider"]["id"],
        inviter_id=members[0], snapshot=dump(snapshot), status="accepted", consultation_id=consult,
        created_at=created, accepted_at=created))
    staff = "provider-shore" if plan["provider"]["id"] == "shore-school" else "provider-forest"
    for n, (uid, body) in enumerate(((members[0], "午前10時集合で、途中に休憩を入れたいです。"),
        (staff, "承知しました。歩く時間は1時間ほどにして、昼食の前に休憩を入れましょう。"),
        (members[1], "ありがとうございます。帰りは17時頃を予定しています。"))):
        insert(conn, "consultation_messages", dict(id=key("shared", index * 3+n), consultation_id=consult,
            author_id=uid, body=body, created_at=created))
    insert(conn, "party_messages", dict(id=key("private", index), party_id=cid, author_id=members[0],
        body="行きたい場所と、手伝えることをここで相談しましょう。", created_at=created))
    return cid, invite, plan, members


def seed_outing(conn, index, base, circle):
    cid, invite, plan, members = circle
    # Only matched 20–40km routes with a published zero-night provider plan
    # qualify for this fictional historical daytrip scenario.
    link = conn.execute("SELECT route_id FROM daytrip_plan_routes WHERE plan_id=?", (plan["id"],)).fetchone()
    if index >= 36 or link is None or plan["nights"]:
        return False
    route = {**next(route for route in ROUTES if route["id"] == link["route_id"]), "zone": "target"}
    start, end = stamp(base, 2+index*2), stamp(base, 2+index*2, 8)
    oid = key("outing", index)
    insert(conn, "daytrip_outings", dict(id=oid, circle_id=cid, title=plan["title"], route_json=dump(route),
        starts_at=start, ends_at=end, day=start[:10], status="confirmed", leader_id=members[0], leader_accepted=1,
        plan_id=plan["id"], provider_id=plan["provider"]["id"], invitation_id=invite, plan_json=dump(plan),
        created_by=members[0], created_at=stamp(base, 9+index*2)))
    for n, uid in enumerate(members):
        points = 100 + int(min(route["one_way_km"]*2, 200)/10) + (50 if n == 0 else 0)
        insert(conn, "daytrip_participants", dict(outing_id=oid, user_id=uid, accepted=1, claimed=1,
            full_route=1, confirmed_by=members[(n+1) % len(members)], provider_verified=1, points=points, revoked=0))
        insert(conn, "daytrip_daily_awards", dict(user_id=uid, day=start[:10], outing_id=oid))
        insert(conn, "daytrip_ledger", dict(id=key("award", index*10+n), outing_id=oid, user_id=uid,
            kind="award", points=points, eligible_points=0, reason="開催の実施と参加を確認", rule_version="D1", created_at=end))
        insert(conn, "daytrip_ledger", dict(id=key("verify", index*10+n), outing_id=oid, user_id=uid,
            kind="verify", points=0, eligible_points=points, reason="事業者が利用を確認", rule_version="D1", created_at=end))
    return True


def enrich(database, settings, at=None):
    base = at or datetime.now(UTC)
    settings.media_dir.mkdir(parents=True, exist_ok=True)
    with database.transaction(True) as conn:
        saved = conn.execute("SELECT value FROM settings WHERE key=?", (PACK,)).fetchone()
        if saved:
            return {**json.loads(saved["value"]), "already_applied": True}
        # Any partial/colliding namespace is investigated rather than overwritten.
        if conn.execute("SELECT 1 FROM users WHERE id LIKE ?", (PREFIX + "%",)).fetchone():
            raise ValueError("Enrichment namespace already exists without manifest")
        seed_people(conn, base)
        seed_plans(conn, base)
        seed_benefits(conn, base)
        photos = seed_posts(conn, settings, base)
        market, outings = Marketplace(database), 0
        for index in range(42):
            circle = seed_circle(conn, market, index, base)
            outings += int(seed_outing(conn, index, base, circle))
        if conn.execute("PRAGMA foreign_key_check").fetchone():
            raise ValueError("Content import has invalid references")
        report = dict(pack=PACK, applied_at=base.isoformat(), users=36, plans=12, benefits=4, posts=48,
            photos=photos, circles=42, consultations=42, shared_messages=126, completed_outings=outings,
            provenance="fictional local content; not survey data or measured tourism outcomes", already_applied=False)
        insert(conn, "settings", dict(key=PACK, value=dump(report)))
        return report


def main():
    parser = argparse.ArgumentParser(description="Add the requested fictional local content pack once")
    parser.add_argument("--apply", action="store_true", required=True)
    parser.parse_args()
    settings = Settings()
    print(json.dumps(enrich(Database(settings.db_path), settings), ensure_ascii=False))


if __name__ == "__main__":
    main()
