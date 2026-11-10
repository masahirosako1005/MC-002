"""Regression boundaries from the EV02 backend security review."""
import asyncio
import hashlib
import sqlite3
from types import SimpleNamespace
from typing import Literal

import pytest
from app import database, security, service
from app.config import Settings
from app.schemas import GrantInput, Input
from pydantic import ValidationError
from test_api import upload
from test_stage import stage_login


def test_hash_profiles_and_unknown_costs():
    salt = "12" * 16
    password = "synthetic-only-password"
    current = database.password_hash(password, salt)
    legacy = hashlib.scrypt(password.encode(), salt=bytes.fromhex(salt), n=16384, r=8, p=1).hex()
    assert current.startswith(database.SCRYPT_PREFIX)
    for encoded in (current, legacy):
        assert database.password_matches(password, salt, encoded)
        assert not database.password_matches("wrong", salt, encoded)
    assert not database.password_matches(password, salt, "scrypt$999999999$8$3$" + legacy)


def test_legacy_login_upgrades_only_success(harness):
    password = "aoi-local-2026"
    with harness.app.state.database.transaction(True) as conn:
        salt = conn.execute("SELECT salt FROM users WHERE id='u-aoi'").fetchone()[0]
        legacy = hashlib.scrypt(password.encode(), salt=bytes.fromhex(salt), n=16384, r=8, p=1).hex()
        conn.execute("UPDATE users SET password_hash=? WHERE id='u-aoi'", (legacy,))
    client = harness.client()
    assert client.write("POST", "/login", dict(username="aoi", password="wrong")).status_code == 401
    with harness.app.state.database.transaction() as conn:
        assert conn.execute("SELECT password_hash FROM users WHERE id='u-aoi'").fetchone()[0] == legacy
    client.login("aoi")
    with harness.app.state.database.transaction() as conn:
        row = conn.execute("SELECT salt,password_hash FROM users WHERE id='u-aoi'").fetchone()
        assert row['salt'] == salt and row['password_hash'].startswith(database.SCRYPT_PREFIX)
    client.login("aoi")


@pytest.mark.parametrize("username", ["missing-user", "ren"])
def test_unknown_and_disabled_accounts_pay_current_kdf(harness, monkeypatch, username):
    with harness.app.state.database.transaction(True) as conn:
        conn.execute("UPDATE users SET login_enabled=0 WHERE username='ren'")
    original = service.password_hash
    calls = []
    def measured(value, salt):
        calls.append(salt)
        return original(value, salt)
    monkeypatch.setattr(service, "password_hash", measured)
    response = harness.client().write("POST", "/login", dict(username=username, password="wrong"))
    assert response.status_code == 401 and calls == ['0' * 32]


@pytest.mark.parametrize("mutation", ["disabled", "credentials"])
def test_login_rechecks_changes_during_kdf_without_holding_write_lock(harness, monkeypatch, mutation):
    original = service.password_hash
    def changed(value, salt):
        candidate = original(value, salt)
        # This independent writer would block/fail if login retained its write lock.
        with harness.app.state.database.transaction(True) as conn:
            if mutation == "disabled":
                conn.execute("UPDATE users SET login_enabled=0 WHERE id='u-aoi'")
            else:
                conn.execute("UPDATE users SET salt=? WHERE id='u-aoi'", ('34' * 16,))
        return candidate
    monkeypatch.setattr(service, "password_hash", changed)
    response = harness.client().write("POST", "/login", dict(username="aoi", password="aoi-local-2026"))
    assert response.status_code == 401
    with harness.app.state.database.transaction() as conn:
        assert conn.execute("SELECT COUNT(*) FROM sessions").fetchone()[0] == 0


def test_stage_rotation_requires_csrf_and_preserves_other_transports(harness):
    client = harness.client('aoi')
    old = stage_login(client, 'aoi')
    other = harness.client()
    stage_login(other, 'forest')
    observer = harness.client()
    observer.client.headers['Authorization'] = 'Bearer ' + old['access_token']
    body = dict(username='ren', password='ren-local-2026')
    assert client.write('POST', '/stage/login', body, headers={'X-CSRF-Token': 'wrong'}).status_code == 403
    assert client.write('POST', '/stage/login', dict(username='ren', password='wrong')).status_code == 401
    assert observer.get('/me').status_code == 200
    stage_login(client, 'ren')
    assert observer.get('/me').status_code == 401
    assert other.get('/me').json()['user']['username'] == 'forest'
    del client.client.headers['Authorization']
    assert client.get('/me').json()['user']['username'] == 'aoi'


@pytest.mark.parametrize('value', ['true', 'yes', 'false', 1, 0, None])
def test_boolean_consent_rejects_coercion(value):
    with pytest.raises(ValidationError):
        GrantInput(community_id='peers', use_for_matching=value, display_in_matches=False, participate=False)
    class ExplicitConfirmation(Input):
        confirmed: Literal[True]
    with pytest.raises(ValidationError):
        ExplicitConfirmation(confirmed=value)


def test_boolean_consent_accepts_explicit_values():
    assert GrantInput(community_id='peers', use_for_matching=True, display_in_matches=False, participate=True).participate is True


def test_failed_photo_fsync_rolls_back_and_cleans_file(harness, monkeypatch):
    client = harness.client('aoi')
    def fail_sync(fd):
        raise OSError('private-fsync-path')
    monkeypatch.setattr(service.os, 'fsync', fail_sync)
    result = upload(client)
    assert result.status_code == 500 and 'private-fsync-path' not in result.text
    with harness.app.state.database.transaction() as conn:
        assert conn.execute("SELECT COUNT(*) FROM media WHERE user_id='u-aoi'").fetchone()[0] == 0
    assert list(harness.settings.media_dir.glob('*.jpg')) == []


def test_photo_collision_does_not_replace_or_delete_existing_file(harness, monkeypatch):
    client = harness.client('aoi')
    first = upload(client)
    assert first.status_code == 200
    mid = first.json()['id']
    target = harness.settings.media_dir / (mid + '.jpg')
    before = target.read_bytes()
    monkeypatch.setattr(service, 'identifier', lambda: mid)
    assert upload(client).status_code == 500
    assert target.read_bytes() == before
    assert client.get('/media/' + mid).status_code == 200


def test_body_has_one_total_deadline(monkeypatch):
    original_timeout = asyncio.timeout
    calls, sent = [], []
    def deadline(seconds):
        calls.append(seconds)
        return original_timeout(0.025)
    # Patch only the module dependency, not the global asyncio module.
    monkeypatch.setattr(security, 'asyncio', SimpleNamespace(timeout=deadline))
    async def app(scope, receive, send):
        pytest.fail('Incomplete body reached application')
    async def receive():
        await asyncio.sleep(0.01)
        return {'type': 'http.request', 'body': b'x', 'more_body': True}
    async def send(message):
        sent.append(message)
    scope = {'type': 'http', 'path': '/api/login', 'method': 'POST', 'client': ('test', 0),
             'headers': [(b'host', b'localhost:8001'), (b'origin', b'http://localhost:8001'), (b'content-type', b'application/json')]}
    asyncio.run(security.SecurityMiddleware(app, Settings())(scope, receive, send))
    assert calls == [15]
    assert sent[0]['status'] == 408
    assert dict(sent[0]['headers'])[b'cache-control'] == b'no-store'


@pytest.mark.parametrize('case', [0, 1])
def test_harness_database_isolation_and_real_seed(database_template, harness, case):
    before = hashlib.sha256(database_template.read_bytes()).hexdigest()
    with sqlite3.connect(database_template) as template:
        expected = template.execute('SELECT COUNT(*) FROM users').fetchone()[0]
        assert template.execute('SELECT COUNT(*) FROM sessions').fetchone()[0] == 0
        assert template.execute('SELECT COUNT(*) FROM settings').fetchone()[0] > 0
    with harness.app.state.database.transaction(True) as conn:
        assert conn.execute('SELECT COUNT(*) FROM users').fetchone()[0] == expected
        assert conn.execute('SELECT COUNT(*) FROM sessions').fetchone()[0] == 0
        assert conn.execute("SELECT name FROM users WHERE id='u-aoi'").fetchone()[0] != 'fixture-isolation'
        conn.execute("UPDATE users SET name='fixture-isolation' WHERE id='u-aoi'")
    harness.client('aoi')
    assert hashlib.sha256(database_template.read_bytes()).hexdigest() == before


def test_rejected_api_consent_does_not_change_saved_preferences(harness):
    client = harness.client('aoi')
    before = client.get('/me/preferences').json()
    body = {'tags': [], 'learn_from_posts': False, 'grants': [
        {'community_id': 'peers', 'use_for_matching': 'yes', 'display_in_matches': True, 'participate': True}]}
    assert client.write('PUT', '/me/preferences', body).status_code == 422
    assert client.get('/me/preferences').json() == before
    body['grants'][0]['use_for_matching'] = True
    assert client.write('PUT', '/me/preferences', body).status_code == 200


def test_parallel_real_kdf_has_one_memory_allocation(monkeypatch):
    import threading
    from concurrent.futures import ThreadPoolExecutor
    original = database.hashlib.scrypt
    active = peak = 0
    lock = threading.Lock()
    def measured(*args, **kwargs):
        nonlocal active, peak
        with lock:
            active += 1
            peak = max(peak, active)
        try:
            return original(*args, **kwargs)
        finally:
            with lock:
                active -= 1
    monkeypatch.setattr(database.hashlib, 'scrypt', measured)
    with ThreadPoolExecutor(max_workers=3) as pool:
        results = list(pool.map(lambda n: database.password_hash('synthetic-' + str(n), '12' * 16), range(3)))
    assert peak == 1 and len(set(results)) == 3


@pytest.mark.parametrize('path,field', [('/login', 'password'), ('/stage/login', 'password'), ('/register', 'password'), ('/account/password', 'current_password'), ('/account/password', 'new_password')])
def test_lone_surrogate_password_rejected_without_log_or_value_leak(harness, caplog, path, field):
    import json
    body = {'username': 'aoi', 'password': 'aoi-local-2026'}
    if path == '/register':
        body = {'username': 'unicode-test', 'name': 'Unicode test', 'password': 'synthetic-strong-password'}
    if path == '/account/password':
        body = {'current_password': 'aoi-local-2026', 'new_password': 'synthetic-strong-password'}
    marker = 'private-surrogate-marker'
    body[field] = marker + chr(0xD800)
    client = harness.client('aoi') if path == '/account/password' else harness.client()
    result = client.request('POST', path, content=json.dumps(body, ensure_ascii=True).encode(), headers={'Content-Type': 'application/json'})
    assert result.status_code == 422
    assert marker not in result.text and marker not in caplog.text
    assert 'UnicodeEncodeError' not in caplog.text


def test_unicode_password_scalar_boundaries():
    from app.account.schemas import PasswordChange
    from app.schemas import Login
    # The 128-character limit is on Unicode scalar values, not UTF-16 code units.
    password = chr(0x1F680) * 128
    assert Login(username='aoi', password=password).password == password
    assert PasswordChange(current_password='old', new_password=password).new_password.get_secret_value() == password
    for invalid in ('', password + chr(0x1F680)):
        with pytest.raises(ValidationError):
            Login(username='aoi', password=invalid)
