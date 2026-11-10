DDL = """CREATE TABLE residence_profiles(
    user_id TEXT PRIMARY KEY REFERENCES users(id),
    area_id TEXT,
    share_analytics INTEGER NOT NULL DEFAULT 0 CHECK(share_analytics IN (0,1)),
    version INTEGER NOT NULL DEFAULT 1 CHECK(version>=1),
    updated_at TEXT NOT NULL,
    CHECK(area_id IS NOT NULL OR share_analytics=0)
)"""


def migrate(database):
    with database.transaction(True) as conn:
        version = conn.execute('PRAGMA user_version').fetchone()[0]
        if version in (11, 12):
            return
        if version != 10:
            raise RuntimeError('Unsupported residence migration source')
        conn.execute(DDL)
        conn.execute('PRAGMA user_version=11')
