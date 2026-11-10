DDL = (
    '''CREATE TABLE program_enrollments(
        user_id TEXT NOT NULL REFERENCES users(id), program_id TEXT NOT NULL,
        version INTEGER NOT NULL DEFAULT 1 CHECK(version>=1), created_at TEXT NOT NULL,
        status TEXT NOT NULL DEFAULT 'active' CHECK(status IN ('active','cancelled')),
        snapshot TEXT NOT NULL,
        PRIMARY KEY(user_id,program_id))''',
    '''CREATE TABLE program_step_links(
        user_id TEXT NOT NULL,program_id TEXT NOT NULL,step_id TEXT NOT NULL,
        outing_id TEXT NOT NULL REFERENCES daytrip_outings(id),updated_at TEXT NOT NULL,
        PRIMARY KEY(user_id,program_id,step_id),UNIQUE(user_id,outing_id),
        FOREIGN KEY(user_id,program_id) REFERENCES program_enrollments(user_id,program_id))''',
    '''CREATE TABLE program_events(
        id TEXT PRIMARY KEY,user_id TEXT NOT NULL REFERENCES users(id),
        program_id TEXT NOT NULL,kind TEXT NOT NULL,body TEXT NOT NULL,created_at TEXT NOT NULL)''',
)


def migrate(database):
    with database.transaction(True) as conn:
        version = conn.execute('PRAGMA user_version').fetchone()[0]
        if version == 12:
            return
        if version != 11:
            raise RuntimeError('Unsupported program migration source')
        for query in DDL:
            conn.execute(query)
        conn.execute('PRAGMA user_version=12')
