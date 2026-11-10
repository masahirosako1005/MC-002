import json

DEFAULT_FILTERS = json.dumps(
    dict(query="", category="", duration="all", schedule="all", area=""),
    separators=(",", ":"),
)

# These triggers latch revocation at the moment it happens: leaving and joining
# again before the next GET must not restore a previous private work context.
_reset_all = (
    "community_id=NULL,circle_id=NULL,page='market',"
    f"filters_json='{DEFAULT_FILTERS}',version=version+1"
)
_reset_circle = (
    "circle_id=NULL,page=CASE WHEN page='circles' THEN 'market' ELSE page END,"
    f"filters_json='{DEFAULT_FILTERS}',version=version+1"
)
_provider_guard = (
    "NOT EXISTS(SELECT 1 FROM provider_staff s JOIN providers p ON p.id=s.provider_id "
    "WHERE s.user_id=user_resume_state.user_id AND s.active=1 AND p.active=1)"
)

DDL = (
    "CREATE TABLE user_resume_state("
    "user_id TEXT PRIMARY KEY REFERENCES users(id) ON DELETE CASCADE,"
    "page TEXT NOT NULL CHECK(page IN ('feed','market','circles','journal','provider','daytrip')),"
    "community_id TEXT REFERENCES communities(id) ON DELETE SET NULL,"
    "circle_id TEXT REFERENCES travel_parties(id) ON DELETE SET NULL,"
    "filters_json TEXT NOT NULL,version INTEGER NOT NULL CHECK(version>=1))",
    "CREATE TRIGGER resume_community_left AFTER UPDATE OF status ON memberships "
    "WHEN NEW.status!='active' BEGIN UPDATE user_resume_state SET "
    + _reset_all
    + " WHERE user_id=NEW.user_id AND community_id=NEW.community_id; END",
    "CREATE TRIGGER resume_community_member_deleted AFTER DELETE ON memberships "
    "BEGIN UPDATE user_resume_state SET "
    + _reset_all
    + " WHERE user_id=OLD.user_id AND community_id=OLD.community_id; END",
    "CREATE TRIGGER resume_community_deleted BEFORE DELETE ON communities "
    "BEGIN UPDATE user_resume_state SET " + _reset_all + " WHERE community_id=OLD.id; END",
    "CREATE TRIGGER resume_circle_member_deleted AFTER DELETE ON travel_party_members "
    "BEGIN UPDATE user_resume_state SET "
    + _reset_circle
    + " WHERE user_id=OLD.user_id AND circle_id=OLD.party_id; END",
    "CREATE TRIGGER resume_group_member_deleted AFTER DELETE ON group_members "
    "BEGIN UPDATE user_resume_state SET "
    + _reset_circle
    + " WHERE user_id=OLD.user_id AND circle_id IN "
    "(SELECT id FROM travel_parties WHERE ko_group_id=OLD.group_id); END",
    "CREATE TRIGGER resume_circle_closed AFTER UPDATE OF status ON travel_parties "
    "WHEN NEW.status!='open' BEGIN UPDATE user_resume_state SET "
    + _reset_circle
    + " WHERE circle_id=NEW.id; END",
    "CREATE TRIGGER resume_circle_deleted BEFORE DELETE ON travel_parties "
    "BEGIN UPDATE user_resume_state SET " + _reset_circle + " WHERE circle_id=OLD.id; END",
    "CREATE TRIGGER resume_staff_disabled AFTER UPDATE OF active ON provider_staff "
    "WHEN NEW.active!=1 BEGIN UPDATE user_resume_state SET page='market',version=version+1 "
    "WHERE user_id=NEW.user_id AND page='provider' AND " + _provider_guard + "; END",
    "CREATE TRIGGER resume_staff_deleted AFTER DELETE ON provider_staff "
    "BEGIN UPDATE user_resume_state SET page='market',version=version+1 "
    "WHERE user_id=OLD.user_id AND page='provider' AND " + _provider_guard + "; END",
    "CREATE TRIGGER resume_provider_disabled AFTER UPDATE OF active ON providers "
    "WHEN NEW.active!=1 BEGIN UPDATE user_resume_state SET page='market',version=version+1 "
    "WHERE page='provider' AND " + _provider_guard + "; END",
    "CREATE TRIGGER resume_account_disabled AFTER UPDATE OF login_enabled ON users "
    "WHEN NEW.login_enabled!=1 BEGIN UPDATE user_resume_state SET "
    + _reset_all
    + " WHERE user_id=NEW.id; END",
)


def migrate(database):
    with database.transaction(True) as conn:
        version = conn.execute("PRAGMA user_version").fetchone()[0]
        if version in (8, 9, 10, 11, 12):
            return
        if version != 7:
            raise RuntimeError("Unsupported personalization migration source")
        for statement in DDL:
            conn.execute(statement)
        conn.execute("PRAGMA user_version=8")
