DDL=(
    "CREATE TABLE occasions(id TEXT PRIMARY KEY,user_id TEXT NOT NULL REFERENCES users(id),kind TEXT NOT NULL,name TEXT NOT NULL,month INTEGER NOT NULL,day INTEGER NOT NULL,repeats_annually INTEGER NOT NULL,year INTEGER,version INTEGER NOT NULL DEFAULT 1,deleted INTEGER NOT NULL DEFAULT 0,created_at TEXT NOT NULL)",
    "CREATE UNIQUE INDEX occasion_birthday ON occasions(user_id) WHERE kind='birthday' AND deleted=0",
    "CREATE TABLE occasion_sharing(occasion_id TEXT NOT NULL REFERENCES occasions(id),party_id TEXT NOT NULL REFERENCES travel_parties(id),share_date INTEGER NOT NULL DEFAULT 0,suggest INTEGER NOT NULL DEFAULT 0,version INTEGER NOT NULL DEFAULT 1,PRIMARY KEY(occasion_id,party_id))",
    "CREATE TABLE occasion_suggestions(id TEXT PRIMARY KEY,occasion_id TEXT NOT NULL REFERENCES occasions(id),party_id TEXT NOT NULL REFERENCES travel_parties(id),occurrence_year INTEGER NOT NULL,UNIQUE(occasion_id,party_id,occurrence_year))",
    "CREATE TABLE occasion_suggestion_states(suggestion_id TEXT NOT NULL REFERENCES occasion_suggestions(id),user_id TEXT NOT NULL REFERENCES users(id),state TEXT NOT NULL,version INTEGER NOT NULL DEFAULT 1,PRIMARY KEY(suggestion_id,user_id))",
    "CREATE TABLE occasion_card_state(card_id TEXT PRIMARY KEY REFERENCES circle_candidate_cards(id),independent INTEGER NOT NULL DEFAULT 0)",
    "CREATE TABLE occasion_card_origins(card_id TEXT NOT NULL REFERENCES circle_candidate_cards(id),occasion_id TEXT NOT NULL REFERENCES occasions(id),party_id TEXT NOT NULL REFERENCES travel_parties(id),occurrence_year INTEGER NOT NULL,occasion_version INTEGER NOT NULL,sharing_version INTEGER NOT NULL,PRIMARY KEY(card_id,occasion_id,occurrence_year))",
    "CREATE TRIGGER occasion_party_member_left AFTER DELETE ON travel_party_members BEGIN UPDATE occasions SET version=version+1 WHERE user_id=OLD.user_id AND id IN(SELECT occasion_id FROM occasion_sharing WHERE party_id=OLD.party_id AND (share_date=1 OR suggest=1)); UPDATE occasion_sharing SET share_date=0,suggest=0,version=version+1 WHERE party_id=OLD.party_id AND occasion_id IN(SELECT id FROM occasions WHERE user_id=OLD.user_id); END",
    "CREATE TRIGGER occasion_community_left AFTER UPDATE OF status ON memberships WHEN NEW.status='left' BEGIN UPDATE occasions SET version=version+1 WHERE user_id=NEW.user_id AND id IN(SELECT occasion_id FROM occasion_sharing WHERE party_id IN(SELECT id FROM travel_parties WHERE community_id=NEW.community_id) AND (share_date=1 OR suggest=1)); UPDATE occasion_sharing SET share_date=0,suggest=0,version=version+1 WHERE occasion_id IN(SELECT id FROM occasions WHERE user_id=NEW.user_id) AND party_id IN(SELECT id FROM travel_parties WHERE community_id=NEW.community_id); END",
    "CREATE TRIGGER occasion_account_disabled AFTER UPDATE OF login_enabled ON users WHEN NEW.login_enabled=0 BEGIN UPDATE occasions SET version=version+1 WHERE user_id=NEW.id; UPDATE occasion_sharing SET share_date=0,suggest=0,version=version+1 WHERE occasion_id IN(SELECT id FROM occasions WHERE user_id=NEW.id); END",
    "CREATE TRIGGER occasion_group_member_left AFTER DELETE ON group_members BEGIN UPDATE occasions SET version=version+1 WHERE user_id=OLD.user_id AND id IN(SELECT occasion_id FROM occasion_sharing WHERE party_id IN(SELECT id FROM travel_parties WHERE ko_group_id=OLD.group_id) AND (share_date=1 OR suggest=1)); UPDATE occasion_sharing SET share_date=0,suggest=0,version=version+1 WHERE occasion_id IN(SELECT id FROM occasions WHERE user_id=OLD.user_id) AND party_id IN(SELECT id FROM travel_parties WHERE ko_group_id=OLD.group_id); END",
)


def migrate(database):
    with database.transaction(True) as conn:
        version=conn.execute('PRAGMA user_version').fetchone()[0]
        if version in (7,8,9,10,11,12):
            return
        if version!=6:
            raise RuntimeError('Unsupported occasions migration source')
        for statement in DDL:
            conn.execute(statement)
        conn.execute('PRAGMA user_version=7')
