import json
import os
import secrets
from ..database import now, password_hash

PROVIDER_ACCOUNTS = (
    ('forest', '森の旅案内', '森', '#4D7161', 'forest-house'),
    ('shore', '海辺の学び舎', '海', '#50788A', 'shore-school'),
)

DDL = (
    "CREATE TABLE IF NOT EXISTS stage_sessions(token_hash TEXT PRIMARY KEY,user_id TEXT NOT NULL REFERENCES users(id),csrf_token TEXT NOT NULL,expires_at TEXT NOT NULL)",
    "CREATE TABLE IF NOT EXISTS providers(id TEXT PRIMARY KEY,name TEXT NOT NULL,description TEXT NOT NULL,area TEXT NOT NULL,active INTEGER NOT NULL)",
    "CREATE TABLE IF NOT EXISTS provider_staff(provider_id TEXT REFERENCES providers(id),user_id TEXT REFERENCES users(id),active INTEGER NOT NULL,PRIMARY KEY(provider_id,user_id))",
    "CREATE TABLE IF NOT EXISTS provider_plans(id TEXT PRIMARY KEY,provider_id TEXT NOT NULL REFERENCES providers(id),body TEXT NOT NULL,status TEXT NOT NULL,version INTEGER NOT NULL,updated_at TEXT NOT NULL)",
    "CREATE TABLE IF NOT EXISTS travel_parties(id TEXT PRIMARY KEY,community_id TEXT NOT NULL REFERENCES communities(id),ko_group_id TEXT REFERENCES ko_groups(id),representative_id TEXT NOT NULL REFERENCES users(id),title TEXT NOT NULL,status TEXT NOT NULL,created_at TEXT NOT NULL)",
    "CREATE TABLE IF NOT EXISTS travel_party_members(party_id TEXT REFERENCES travel_parties(id),user_id TEXT REFERENCES users(id),PRIMARY KEY(party_id,user_id))",
    "CREATE TABLE IF NOT EXISTS travel_requirements(party_id TEXT PRIMARY KEY REFERENCES travel_parties(id),body TEXT NOT NULL,version INTEGER NOT NULL,confirmed_by TEXT NOT NULL REFERENCES users(id),confirmed_at TEXT NOT NULL)",
    "CREATE TABLE IF NOT EXISTS party_messages(id TEXT PRIMARY KEY,party_id TEXT NOT NULL REFERENCES travel_parties(id),author_id TEXT NOT NULL REFERENCES users(id),body TEXT NOT NULL,created_at TEXT NOT NULL)",
    "CREATE TABLE IF NOT EXISTS condition_drafts(id TEXT PRIMARY KEY,party_id TEXT NOT NULL REFERENCES travel_parties(id),body TEXT NOT NULL,created_at TEXT NOT NULL)",
    "CREATE TABLE IF NOT EXISTS recommendation_runs(id TEXT PRIMARY KEY,party_id TEXT NOT NULL REFERENCES travel_parties(id),body TEXT NOT NULL,created_at TEXT NOT NULL)",
    "CREATE TABLE IF NOT EXISTS plan_selections(id TEXT PRIMARY KEY,party_id TEXT NOT NULL REFERENCES travel_parties(id),plan_id TEXT NOT NULL REFERENCES provider_plans(id),provider_id TEXT NOT NULL REFERENCES providers(id),snapshot TEXT NOT NULL,selected_by TEXT NOT NULL REFERENCES users(id),status TEXT NOT NULL,created_at TEXT NOT NULL)",
    "CREATE UNIQUE INDEX IF NOT EXISTS one_active_selection ON plan_selections(party_id) WHERE status='active'",
    "CREATE TABLE IF NOT EXISTS consultations(id TEXT PRIMARY KEY,selection_id TEXT NOT NULL UNIQUE REFERENCES plan_selections(id),status TEXT NOT NULL,version INTEGER NOT NULL DEFAULT 1,created_at TEXT NOT NULL)",
    "CREATE TABLE IF NOT EXISTS consultation_messages(id TEXT PRIMARY KEY,consultation_id TEXT NOT NULL REFERENCES consultations(id),author_id TEXT NOT NULL REFERENCES users(id),body TEXT NOT NULL,created_at TEXT NOT NULL)",
    "CREATE TABLE IF NOT EXISTS operation_keys(actor_id TEXT REFERENCES users(id),operation TEXT NOT NULL,request_key TEXT NOT NULL,payload_hash TEXT NOT NULL,result_id TEXT NOT NULL,PRIMARY KEY(actor_id,operation,request_key))",
)


def migrate(database):
    """One atomic, additive migration; existing user data is preserved."""
    with database.transaction(True) as conn:
        version = conn.execute('PRAGMA user_version').fetchone()[0]
        if version in (2, 3, 4, 5):
            return
        if version != 1:
            raise RuntimeError('Unsupported marketplace migration source')
        for statement in DDL:
            conn.execute(statement)
        for username, name, initials, color, pid in PROVIDER_ACCOUNTS:
            uid = 'provider-' + username
            salt = secrets.token_hex(16)
            password = os.getenv('KO_PASSWORD_' + username.upper(), username + '-local-2026')
            conn.execute('INSERT INTO users VALUES(?,?,?,?,?,?,?,1)', (uid, username, name, initials, color, salt, password_hash(password, salt)))
            conn.execute('INSERT INTO preferences(user_id,tags,learn_from_posts) VALUES(?,?,0)', (uid, '[]'))
            conn.execute('INSERT INTO providers VALUES(?,?,?,?,1)', (pid, name, '仲間の人数に合わせた旅の相談窓口。', '軽井沢周辺' if username == 'forest' else '海辺のまち'))
            conn.execute('INSERT INTO provider_staff VALUES(?,?,1)', (pid, uid))
        for pid, provider, title, lo, hi, nights, price, tags, places in (
            ('forest-six', 'forest-house', '6人で森とカフェをめぐる2泊3日', 4, 8, 2, 28000, ['mountain','cafe','nature'], ['木立の散策路','森の喫茶室','高原の展望広場']),
            ('shore-school', 'shore-school', '30人からの海辺の学び・2泊3日', 30, 60, 2, 24000, ['coast','nature','food'], ['海辺の学習広場','港の食文化体験室','浜の観察路']),
            ('forest-day', 'forest-house', '森を歩く日帰りの相談プラン', 1, 12, 0, 6000, ['mountain','walk','cafe'], ['森の喫茶室']),
        ):
            body = dict(title=title, summary='仲間と相談して行程を調整できます。', area='軽井沢周辺' if provider == 'forest-house' else '海辺のまち', min_people=lo, max_people=hi, nights=nights, price_yen=price, price_basis='per_person', price_scope='plan_only', price_note='宿泊・体験の概算。出発地からの交通費は含みません。営業・空席は未確認。', tags=tags,
                        itinerary=[dict(day=i+1, period='afternoon', place=place, description='この場所での体験を相談します。', travel_minutes=None) for i, place in enumerate(places)])
            conn.execute('INSERT INTO provider_plans VALUES(?,?,?,\'published\',1,?)', (pid, provider, json.dumps(body,ensure_ascii=False), now()))
        conn.execute('PRAGMA user_version=2')
