"""The content pack must preserve existing input and be safely repeatable."""
import json
from dataclasses import replace
from datetime import UTC, datetime
from pathlib import Path

from app.enrichment import PACK, enrich
from app.marketplace.schemas import ProviderPlanInput
from app.marketplace.service import Marketplace


def test_content_pack_is_additive_repeatable_and_coherent(harness):
    db = harness.app.state.database
    with db.transaction() as conn:
        original_users = [tuple(r) for r in conn.execute('SELECT * FROM users ORDER BY id')]
        original_posts = [tuple(r) for r in conn.execute('SELECT * FROM posts ORDER BY id')]
    report = enrich(db, harness.settings, datetime(2026, 11, 10, 0, tzinfo=UTC))
    assert report['users'] == 36 and report['posts'] == 48
    assert report['consultations'] == 42 and report['completed_outings'] == 30
    repeat = enrich(db, harness.settings, datetime(2026, 11, 12, 0, tzinfo=UTC))
    assert repeat['already_applied'] and repeat['applied_at'] == report['applied_at']
    with db.transaction() as conn:
        assert original_users == [tuple(r) for r in conn.execute("SELECT * FROM users WHERE id NOT LIKE 'extra26-%' ORDER BY id")]
        assert original_posts == [tuple(r) for r in conn.execute("SELECT * FROM posts WHERE id NOT LIKE 'extra26-%' ORDER BY id")]
        assert conn.execute('PRAGMA foreign_key_check').fetchall() == []
        assert conn.execute("SELECT COUNT(*) FROM posts WHERE id LIKE 'extra26-%'").fetchone()[0] == 48
        for row in conn.execute("SELECT body FROM provider_plans WHERE id LIKE 'extra26-%'"):
            ProviderPlanInput.model_validate({**json.loads(row['body']), 'status': 'published'})
        assert conn.execute("SELECT COUNT(*) FROM daytrip_ledger WHERE user_id IN ('u-aoi','u-ren','u-mio')").fetchone()[0] == 0
        assert conn.execute("SELECT COUNT(*) FROM daytrip_outings WHERE julianday(created_at)>julianday(starts_at)").fetchone()[0] == 0
        assert conn.execute('SELECT value FROM settings WHERE key=?', (PACK,)).fetchone()
    market = Marketplace(db)
    forest = market.consultations('provider-forest')['items']
    assert len(forest) == 35
    for item in forest:
        assert 'interests' not in item['selection']['shared_conditions']
        assert 'snapshot' not in item


def test_content_pack_rolls_back_on_collision(harness):
    db = harness.app.state.database
    with db.transaction(True) as conn:
        conn.execute("INSERT INTO settings VALUES('existing-user-note','keep this')")
        conn.execute("INSERT INTO users VALUES('extra26-person-999','collision','Existing','E','#000','','',0)")
    import pytest
    with pytest.raises(ValueError, match='namespace'):
        enrich(db, harness.settings)
    with db.transaction() as conn:
        assert conn.execute("SELECT COUNT(*) FROM posts WHERE id LIKE 'extra26-%'").fetchone()[0] == 0
        assert conn.execute("SELECT value FROM settings WHERE key='existing-user-note'").fetchone()[0] == 'keep this'


def test_content_photos_are_local_sanitized_and_not_duplicated(harness):
    from PIL import Image
    settings = replace(harness.settings, seed_asset_dir=Path(__file__).resolve().parents[2] / 'community' / 'assets')
    report = enrich(harness.app.state.database, settings)
    assert report['photos'] == 24
    assert enrich(harness.app.state.database, settings)['already_applied']
    files = list(settings.media_dir.glob('extra26-*.jpg'))
    assert len(files) == 24
    for file in files:
        with Image.open(file) as image:
            assert image.format == 'JPEG' and not image.getexif()
