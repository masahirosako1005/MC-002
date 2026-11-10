"""Explicit Nnishi analytics membership for the local city's initial operators."""

CITY_KEY = "n-nishi"
INITIAL_PROVIDERS = ("forest-house", "shore-school")


def migrate(database):
    """Register initial city operators once, without restoring withdrawn entries."""
    with database.transaction(True) as conn:
        for provider_id in INITIAL_PROVIDERS:
            # City membership is configured, never inferred from editable area text.
            if conn.execute("SELECT 1 FROM providers WHERE id=?", (provider_id,)).fetchone():
                conn.execute(
                    "INSERT OR IGNORE INTO settings(key,value) VALUES(?,?)",
                    (f"city-provider:{CITY_KEY}:{provider_id}", "1"),
                )
