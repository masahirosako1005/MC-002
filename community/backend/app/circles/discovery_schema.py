DDL = (
    "CREATE TABLE circle_candidate_cards(id TEXT PRIMARY KEY,party_id TEXT NOT NULL REFERENCES travel_parties(id),plan_id TEXT NOT NULL REFERENCES provider_plans(id),plan_version INTEGER NOT NULL,snapshot TEXT NOT NULL,saved_by TEXT NOT NULL REFERENCES users(id),created_at TEXT NOT NULL,version INTEGER NOT NULL DEFAULT 1,UNIQUE(party_id,plan_id))",
    "CREATE INDEX circle_card_party ON circle_candidate_cards(party_id,created_at)",
)


def migrate(database):
    with database.transaction(True) as conn:
        version = conn.execute('PRAGMA user_version').fetchone()[0]
        if version in (5, 6, 7):
            return
        if version != 4:
            raise RuntimeError('Unsupported discovery migration source')
        for statement in DDL:
            conn.execute(statement)
        conn.execute('PRAGMA user_version=5')
