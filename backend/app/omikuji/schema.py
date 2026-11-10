"""Independent additive module migration; the application schema remains version 12."""
import secrets

DDL = (
    """CREATE TABLE omikuji_policies(provider_id TEXT PRIMARY KEY REFERENCES providers(id),
       enabled INTEGER NOT NULL CHECK(enabled IN (0,1)), monthly_budget_yen INTEGER NOT NULL CHECK(monthly_budget_yen BETWEEN 0 AND 10000),
       version INTEGER NOT NULL CHECK(version>=1),updated_at TEXT NOT NULL)""",
    """CREATE TABLE omikuji_codes(id TEXT PRIMARY KEY,provider_id TEXT NOT NULL REFERENCES providers(id),
       code_hash TEXT NOT NULL UNIQUE,created_at TEXT NOT NULL,expires_at TEXT NOT NULL,consumed_at TEXT,
       created_by TEXT NOT NULL REFERENCES users(id))""",
    """CREATE TABLE omikuji_draws(id TEXT PRIMARY KEY,user_id TEXT NOT NULL REFERENCES users(id),
       provider_id TEXT NOT NULL REFERENCES providers(id),month TEXT NOT NULL,code_id TEXT NOT NULL UNIQUE REFERENCES omikuji_codes(id),
       client_request_id TEXT NOT NULL,amount_yen INTEGER NOT NULL CHECK(amount_yen IN (0,100,200,300)),
       rank_level INTEGER NOT NULL CHECK(rank_level BETWEEN 1 AND 10),created_at TEXT NOT NULL,
       UNIQUE(user_id,month),UNIQUE(user_id,client_request_id))""",
    """CREATE TABLE omikuji_rewards(id TEXT PRIMARY KEY,draw_id TEXT NOT NULL UNIQUE REFERENCES omikuji_draws(id),
       expires_at TEXT NOT NULL,redeemed_at TEXT,redeemed_by TEXT REFERENCES users(id),purchase_yen INTEGER,
       no_other_discount INTEGER NOT NULL DEFAULT 0 CHECK(no_other_discount IN (0,1)))""",
    """CREATE TABLE omikuji_attempts(user_id TEXT PRIMARY KEY REFERENCES users(id),window INTEGER NOT NULL,attempts INTEGER NOT NULL)""",
    "CREATE INDEX omikuji_provider_month ON omikuji_draws(provider_id,month)",
)


def migrate(database):
    with database.transaction(True) as conn:
        row = conn.execute("SELECT value FROM settings WHERE key='omikuji-schema'").fetchone()
        if row:
            if row[0] != '1':
                raise RuntimeError('Unsupported omikuji module schema')
            return
        if conn.execute('PRAGMA user_version').fetchone()[0] != 12:
            raise RuntimeError('Omikuji requires application schema 12')
        for query in DDL:
            conn.execute(query)
        conn.execute("INSERT INTO settings VALUES('omikuji-code-pepper',?)", (secrets.token_hex(32),))
        conn.execute("INSERT INTO settings VALUES('omikuji-schema','1')")
