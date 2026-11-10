from app.city_registry import migrate


def test_city_membership_preserves_withdrawal_and_existing_data(harness):
    db = harness.app.state.database
    with db.transaction(True) as conn:
        initial = dict(conn.execute(
            "SELECT key,value FROM settings WHERE key LIKE 'city-provider:%'"
        ).fetchall())
        assert initial == {
            "city-provider:n-nishi:forest-house": "1",
            "city-provider:n-nishi:shore-school": "1",
        }
        conn.execute("UPDATE settings SET value='0' WHERE key=?", (
            "city-provider:n-nishi:shore-school",
        ))
        names = [tuple(row) for row in conn.execute("SELECT id,name,area FROM providers ORDER BY id")]
    migrate(db)
    with db.transaction() as conn:
        assert conn.execute("SELECT value FROM settings WHERE key=?", (
            "city-provider:n-nishi:shore-school",
        )).fetchone()[0] == "0"
        assert names == [tuple(row) for row in conn.execute("SELECT id,name,area FROM providers ORDER BY id")]
