DDL = (
    "CREATE TABLE journal_journeys(id TEXT PRIMARY KEY,user_id TEXT NOT NULL REFERENCES users(id),title TEXT NOT NULL,version INTEGER NOT NULL DEFAULT 1,created_at TEXT NOT NULL)",
    "CREATE INDEX journal_journeys_owner ON journal_journeys(user_id)",
    "CREATE TABLE journal_visits(id TEXT PRIMARY KEY,user_id TEXT NOT NULL REFERENCES users(id),journey_id TEXT NOT NULL REFERENCES journal_journeys(id) ON DELETE CASCADE,prefecture_id TEXT NOT NULL,visited_on TEXT NOT NULL,place_label TEXT NOT NULL,latitude REAL,longitude REAL,media_id TEXT REFERENCES media(id),source TEXT NOT NULL CHECK(source IN ('manual','exif')),visibility TEXT NOT NULL CHECK(visibility IN ('private','community')),community_id TEXT REFERENCES communities(id),version INTEGER NOT NULL DEFAULT 1,created_at TEXT NOT NULL,updated_at TEXT NOT NULL)",
    "CREATE INDEX journal_visits_owner ON journal_visits(user_id,journey_id)",
    "CREATE UNIQUE INDEX journal_one_photo_visit ON journal_visits(media_id) WHERE media_id IS NOT NULL",
    "CREATE TABLE journal_location_candidates(media_id TEXT PRIMARY KEY REFERENCES media(id),latitude REAL NOT NULL,longitude REAL NOT NULL,created_at TEXT NOT NULL)",
    "CREATE TABLE journal_profiles(user_id TEXT PRIMARY KEY REFERENCES users(id),share_achievements INTEGER NOT NULL DEFAULT 0,version INTEGER NOT NULL DEFAULT 1)",
    "CREATE TRIGGER journal_visit_added AFTER INSERT ON journal_visits BEGIN UPDATE journal_journeys SET version=version+1 WHERE id=NEW.journey_id; END",
    "CREATE TRIGGER journal_visit_changed AFTER UPDATE ON journal_visits BEGIN UPDATE journal_journeys SET version=version+1 WHERE id IN (OLD.journey_id,NEW.journey_id); END",
    "CREATE TRIGGER journal_visit_removed AFTER DELETE ON journal_visits BEGIN UPDATE journal_journeys SET version=version+1 WHERE id=OLD.journey_id; END",
    "CREATE TRIGGER journal_photo_deleted AFTER UPDATE OF deleted ON media WHEN NEW.deleted=1 BEGIN DELETE FROM journal_visits WHERE media_id=NEW.id; DELETE FROM journal_location_candidates WHERE media_id=NEW.id; END",
    "CREATE TRIGGER journal_membership_left AFTER UPDATE OF status ON memberships WHEN NEW.status='left' BEGIN UPDATE journal_visits SET visibility='private',community_id=NULL,version=version+1 WHERE user_id=NEW.user_id AND community_id=NEW.community_id; END",
)


def migrate(database):
    with database.transaction(True) as conn:
        version = conn.execute('PRAGMA user_version').fetchone()[0]
        if version in (3, 4, 5):
            return
        if version != 2:
            raise RuntimeError('Unsupported journal migration source')
        for statement in DDL:
            conn.execute(statement)
        conn.execute('PRAGMA user_version=3')
