DDL=(
    "CREATE TABLE reflection_sessions(id TEXT PRIMARY KEY,party_id TEXT NOT NULL REFERENCES travel_parties(id),provider_id TEXT NOT NULL REFERENCES providers(id),invitation_id TEXT NOT NULL REFERENCES circle_provider_invitations(id),ended_on TEXT NOT NULL,trip_finished INTEGER NOT NULL,version INTEGER NOT NULL DEFAULT 1,epoch INTEGER NOT NULL DEFAULT 1,participants_json TEXT NOT NULL,participants_valid INTEGER NOT NULL DEFAULT 1,created_at TEXT NOT NULL,UNIQUE(party_id,provider_id))",
    "CREATE INDEX reflection_provider ON reflection_sessions(provider_id)",
    "CREATE TABLE reflection_participants(reflection_id TEXT NOT NULL REFERENCES reflection_sessions(id),epoch INTEGER NOT NULL,user_id TEXT NOT NULL REFERENCES users(id),used_service INTEGER NOT NULL DEFAULT 0,consented INTEGER NOT NULL DEFAULT 0,version INTEGER NOT NULL DEFAULT 1,updated_at TEXT NOT NULL,PRIMARY KEY(reflection_id,epoch,user_id))",
    "CREATE TABLE reflection_messages(id TEXT PRIMARY KEY,reflection_id TEXT NOT NULL REFERENCES reflection_sessions(id),epoch INTEGER NOT NULL,author_id TEXT NOT NULL REFERENCES users(id),body TEXT NOT NULL,version INTEGER NOT NULL DEFAULT 1,source_version INTEGER NOT NULL DEFAULT 1,deleted INTEGER NOT NULL DEFAULT 0,auto_json TEXT,override_json TEXT,override_source_version INTEGER,created_at TEXT NOT NULL,updated_at TEXT NOT NULL)",
    "CREATE INDEX reflection_message_scope ON reflection_messages(reflection_id,epoch,deleted)",
    "CREATE TRIGGER reflection_member_added AFTER INSERT ON travel_party_members BEGIN UPDATE reflection_sessions SET participants_valid=0,version=version+1 WHERE party_id=NEW.party_id; END",
    "CREATE TRIGGER reflection_member_removed AFTER DELETE ON travel_party_members BEGIN UPDATE reflection_sessions SET participants_valid=0,version=version+1 WHERE party_id=OLD.party_id; END",
    "CREATE TRIGGER reflection_membership_changed AFTER UPDATE OF status ON memberships WHEN OLD.status!=NEW.status BEGIN UPDATE reflection_sessions SET participants_valid=0,version=version+1 WHERE party_id IN (SELECT id FROM travel_parties WHERE community_id=NEW.community_id) AND id IN (SELECT reflection_id FROM reflection_participants WHERE user_id=NEW.user_id); END",
    "CREATE TRIGGER reflection_account_changed AFTER UPDATE OF login_enabled ON users WHEN OLD.login_enabled!=NEW.login_enabled BEGIN UPDATE reflection_sessions SET participants_valid=0,version=version+1 WHERE id IN (SELECT reflection_id FROM reflection_participants WHERE user_id=NEW.id); END",
    "CREATE TRIGGER reflection_staff_added AFTER INSERT ON provider_staff BEGIN UPDATE reflection_sessions SET participants_valid=0,version=version+1 WHERE provider_id=NEW.provider_id AND party_id IN (SELECT party_id FROM travel_party_members WHERE user_id=NEW.user_id); END",
    "CREATE TRIGGER reflection_staff_removed AFTER DELETE ON provider_staff BEGIN UPDATE reflection_sessions SET participants_valid=0,version=version+1 WHERE provider_id=OLD.provider_id AND party_id IN (SELECT party_id FROM travel_party_members WHERE user_id=OLD.user_id); END",
)


def migrate(database):
    with database.transaction(True) as conn:
        version=conn.execute('PRAGMA user_version').fetchone()[0]
        if version in (6,7,8):
            return
        if version!=5:
            raise RuntimeError('Unsupported reflections migration source')
        for statement in DDL:
            conn.execute(statement)
        conn.execute('PRAGMA user_version=6')
