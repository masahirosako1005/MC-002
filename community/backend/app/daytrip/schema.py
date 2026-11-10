from ..personalization.schema import DDL as RESUME_DDL

DDL = (
    "CREATE TABLE daytrip_plan_routes(plan_id TEXT PRIMARY KEY REFERENCES provider_plans(id),route_id TEXT NOT NULL,updated_by TEXT NOT NULL REFERENCES users(id),updated_at TEXT NOT NULL)",
    "CREATE TABLE daytrip_outings(id TEXT PRIMARY KEY,circle_id TEXT NOT NULL REFERENCES travel_parties(id),title TEXT NOT NULL,route_json TEXT NOT NULL,starts_at TEXT NOT NULL,ends_at TEXT NOT NULL,day TEXT NOT NULL,status TEXT NOT NULL CHECK(status IN ('scheduled','reporting','confirmed','cancelled')),version INTEGER NOT NULL DEFAULT 1,leader_id TEXT NOT NULL REFERENCES users(id),leader_accepted INTEGER NOT NULL DEFAULT 0,plan_id TEXT REFERENCES provider_plans(id),provider_id TEXT REFERENCES providers(id),invitation_id TEXT REFERENCES circle_provider_invitations(id),plan_json TEXT,created_by TEXT NOT NULL REFERENCES users(id),created_at TEXT NOT NULL)",
    "CREATE INDEX daytrip_circle ON daytrip_outings(circle_id,starts_at)",
    "CREATE TABLE daytrip_participants(outing_id TEXT NOT NULL REFERENCES daytrip_outings(id),user_id TEXT NOT NULL REFERENCES users(id),accepted INTEGER NOT NULL DEFAULT 0,claimed INTEGER NOT NULL DEFAULT 0,full_route INTEGER NOT NULL DEFAULT 0,confirmed_by TEXT REFERENCES users(id),provider_verified INTEGER NOT NULL DEFAULT 0,points INTEGER NOT NULL DEFAULT 0,revoked INTEGER NOT NULL DEFAULT 0,PRIMARY KEY(outing_id,user_id))",
    "CREATE TABLE daytrip_events(id TEXT PRIMARY KEY,outing_id TEXT NOT NULL REFERENCES daytrip_outings(id),actor_id TEXT NOT NULL REFERENCES users(id),kind TEXT NOT NULL,body TEXT NOT NULL,created_at TEXT NOT NULL)",
    "CREATE TABLE daytrip_daily_awards(user_id TEXT NOT NULL REFERENCES users(id),day TEXT NOT NULL,outing_id TEXT NOT NULL REFERENCES daytrip_outings(id),PRIMARY KEY(user_id,day))",
    "CREATE TABLE daytrip_ledger(id TEXT PRIMARY KEY,outing_id TEXT NOT NULL REFERENCES daytrip_outings(id),user_id TEXT NOT NULL REFERENCES users(id),kind TEXT NOT NULL CHECK(kind IN ('award','verify','reverse')),points INTEGER NOT NULL,eligible_points INTEGER NOT NULL,reason TEXT NOT NULL,rule_version TEXT NOT NULL,created_at TEXT NOT NULL)",
    "CREATE INDEX daytrip_ledger_owner ON daytrip_ledger(user_id,created_at)",
    "CREATE TABLE daytrip_benefits(id TEXT PRIMARY KEY,provider_id TEXT NOT NULL REFERENCES providers(id),plan_id TEXT NOT NULL REFERENCES provider_plans(id),title TEXT NOT NULL,min_rank INTEGER NOT NULL,discount_type TEXT NOT NULL CHECK(discount_type IN ('amount','percent')),discount_value INTEGER NOT NULL,max_discount_yen INTEGER NOT NULL,max_redemptions INTEGER NOT NULL,starts_on TEXT NOT NULL,ends_on TEXT NOT NULL,status TEXT NOT NULL CHECK(status IN ('published','closed')),version INTEGER NOT NULL DEFAULT 1,created_at TEXT NOT NULL)",
    "CREATE TABLE daytrip_redemptions(id TEXT PRIMARY KEY,benefit_id TEXT NOT NULL REFERENCES daytrip_benefits(id),outing_id TEXT NOT NULL REFERENCES daytrip_outings(id),user_id TEXT NOT NULL REFERENCES users(id),provider_id TEXT NOT NULL REFERENCES providers(id),status TEXT NOT NULL CHECK(status IN ('reserved','redeemed','cancelled')),version INTEGER NOT NULL DEFAULT 1,original_yen INTEGER NOT NULL,discount_yen INTEGER NOT NULL,total_yen INTEGER NOT NULL,conditions_json TEXT NOT NULL,adjustment_required INTEGER NOT NULL DEFAULT 0,created_at TEXT NOT NULL,UNIQUE(outing_id,user_id))",
)

# Permission revocation is latched: rejoining must not resurrect an old
# pre-departure consent. Earned historical points require an explicit correction.
REVOCATION_DDL = (
    "CREATE TRIGGER daytrip_leader_revoked AFTER UPDATE OF revoked ON daytrip_participants WHEN NEW.revoked=1 AND OLD.revoked=0 BEGIN UPDATE daytrip_outings SET leader_accepted=0 WHERE id=NEW.outing_id AND leader_id=NEW.user_id AND julianday(starts_at)>julianday('now'); END",
    "CREATE TRIGGER daytrip_member_left AFTER DELETE ON travel_party_members BEGIN UPDATE daytrip_participants SET revoked=1 WHERE user_id=OLD.user_id AND outing_id IN(SELECT id FROM daytrip_outings WHERE circle_id=OLD.party_id); UPDATE daytrip_outings SET version=version+1 WHERE circle_id=OLD.party_id; END",
    "CREATE TRIGGER daytrip_community_left AFTER UPDATE OF status ON memberships WHEN NEW.status!='active' BEGIN UPDATE daytrip_participants SET revoked=1 WHERE user_id=NEW.user_id AND outing_id IN(SELECT o.id FROM daytrip_outings o JOIN travel_parties p ON p.id=o.circle_id WHERE p.community_id=NEW.community_id); UPDATE daytrip_outings SET version=version+1 WHERE circle_id IN(SELECT id FROM travel_parties WHERE community_id=NEW.community_id); END",
    "CREATE TRIGGER daytrip_group_left AFTER DELETE ON group_members BEGIN UPDATE daytrip_participants SET revoked=1 WHERE user_id=OLD.user_id AND outing_id IN(SELECT o.id FROM daytrip_outings o JOIN travel_parties p ON p.id=o.circle_id WHERE p.ko_group_id=OLD.group_id); UPDATE daytrip_outings SET version=version+1 WHERE circle_id IN(SELECT id FROM travel_parties WHERE ko_group_id=OLD.group_id); END",
    "CREATE TRIGGER daytrip_account_disabled AFTER UPDATE OF login_enabled ON users WHEN NEW.login_enabled=0 BEGIN UPDATE daytrip_participants SET revoked=1 WHERE user_id=NEW.id; END",
)


RELEASE_DDL = (
    "CREATE TRIGGER daytrip_release_participant AFTER UPDATE OF revoked ON daytrip_participants WHEN NEW.revoked=1 AND OLD.revoked=0 BEGIN UPDATE daytrip_redemptions SET status='cancelled',version=version+1 WHERE outing_id=NEW.outing_id AND user_id=NEW.user_id AND status='reserved'; END",
    "CREATE TRIGGER daytrip_release_circle AFTER UPDATE OF status ON travel_parties WHEN NEW.status!='open' BEGIN UPDATE daytrip_redemptions SET status='cancelled',version=version+1 WHERE status='reserved' AND outing_id IN(SELECT id FROM daytrip_outings WHERE circle_id=NEW.id); END",
    "CREATE TRIGGER daytrip_release_invitation AFTER UPDATE OF status ON circle_provider_invitations WHEN NEW.status!='accepted' BEGIN UPDATE daytrip_redemptions SET status='cancelled',version=version+1 WHERE status='reserved' AND outing_id IN(SELECT id FROM daytrip_outings WHERE invitation_id=NEW.id); END",
)


def add_schema9(conn):
    for statement in DDL + REVOCATION_DDL:
        conn.execute(statement)
    # Rebuild only the resume CHECK constraint. Preserve every existing row
    # and recreate the exact revocation triggers in the same transaction.
    triggers = conn.execute("SELECT name,sql FROM sqlite_master WHERE type='trigger' AND name LIKE 'resume_%'").fetchall()
    for trigger in triggers:
        conn.execute('DROP TRIGGER "' + trigger['name'].replace('"', '""') + '"')
    conn.execute(RESUME_DDL[0].replace('CREATE TABLE user_resume_state(', 'CREATE TABLE user_resume_state_next('))
    conn.execute('INSERT INTO user_resume_state_next SELECT * FROM user_resume_state')
    conn.execute('DROP TABLE user_resume_state')
    conn.execute('ALTER TABLE user_resume_state_next RENAME TO user_resume_state')
    for trigger in triggers:
        conn.execute(trigger['sql'])


def migrate(database):
    with database.transaction(True) as conn:
        version = conn.execute('PRAGMA user_version').fetchone()[0]
        if version in (10, 11):
            return
        if version not in (8, 9):
            raise RuntimeError('Unsupported daytrip migration source')
        if version == 8:
            add_schema9(conn)
        for statement in RELEASE_DDL:
            conn.execute(statement)
        # Repair only unusable, unconsumed reservations left by schema 9.
        # Historical redeemed prices and unrelated people's holds are immutable.
        conn.execute("""UPDATE daytrip_redemptions SET status='cancelled',version=version+1
            WHERE status='reserved' AND EXISTS(
                SELECT 1 FROM daytrip_outings o
                JOIN daytrip_participants a ON a.outing_id=o.id AND a.user_id=daytrip_redemptions.user_id
                JOIN travel_parties p ON p.id=o.circle_id
                LEFT JOIN circle_provider_invitations i ON i.id=o.invitation_id
                WHERE o.id=daytrip_redemptions.outing_id AND
                (a.revoked=1 OR o.status='cancelled' OR p.status!='open' OR COALESCE(i.status,'')!='accepted'))""")
        conn.execute('PRAGMA user_version=10')
