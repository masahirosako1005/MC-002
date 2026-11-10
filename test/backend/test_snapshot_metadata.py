"""Backup metadata compatibility only; no Docker or live data operations."""
import importlib.util
import json
import sys
from pathlib import Path

import pytest


@pytest.fixture
def snapshot_script(tmp_path, monkeypatch):
    path = Path(__file__).resolve().parents[2] / 'scripts/full_snapshot.py'
    spec = importlib.util.spec_from_file_location('tested_full_snapshot',path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    monkeypatch.setattr(module,'ROOT',tmp_path)
    monkeypatch.setattr(module,'BACKUPS',tmp_path / 'backups')
    monkeypatch.setattr(module,'running_app',lambda:dict(Config={'Env':['APP_DB_PATH=/app/data/community.db']},Image='fixture-image',State={'Running':False}))
    calls = []
    def helper(operation,snapshot,image,**kwargs):
        calls.append((operation,snapshot,image,kwargs))
        return {'fixture':True}
    monkeypatch.setattr(module,'helper',helper)
    return module,calls


@pytest.mark.parametrize('manifest', [None, {'revision':'retained-legacy-model'}])
def test_backup_model_metadata_is_optional_without_inference(snapshot_script, monkeypatch, manifest):
    module,calls = snapshot_script
    if manifest is not None:
        model_folder = module.ROOT / 'models'
        model_folder.mkdir()
        (model_folder / 'manifest.json').write_text(json.dumps(manifest),encoding='utf-8')
    monkeypatch.setattr(sys,'argv',['full_snapshot.py','backup','--allow-stop'])
    module.main()
    assert len(calls) == 1 and calls[0][0] == 'backup'
    metadata = json.loads((calls[0][1] / 'runtime.json').read_text(encoding='utf-8'))
    assert metadata['model_manifest'] == manifest
    assert metadata['image'] == 'fixture-image'
    if manifest is None:
        assert not (module.ROOT / 'models').exists()


@pytest.mark.parametrize('manifest', [None, {'revision':'retained-legacy-model'}])
def test_verify_accepts_old_and_model_free_metadata(snapshot_script, monkeypatch, manifest):
    module,calls = snapshot_script
    snapshot = module.BACKUPS / 'kept-snapshot'
    snapshot.mkdir(parents=True)
    metadata = {'image':'prior-image','model_manifest':manifest}
    (snapshot / 'runtime.json').write_text(json.dumps(metadata),encoding='utf-8')
    monkeypatch.setattr(sys,'argv',['full_snapshot.py','verify','--snapshot',str(snapshot)])
    module.main()
    assert calls == [('verify',snapshot,'prior-image',{})]
    assert json.loads((snapshot / 'runtime.json').read_text(encoding='utf-8')) == metadata


@pytest.mark.parametrize('operation', ['verify', 'restore'])
def test_explicit_local_helper_keeps_saved_metadata(snapshot_script, monkeypatch, operation):
    module, calls = snapshot_script
    snapshot = module.BACKUPS / 'kept-snapshot'
    snapshot.mkdir(parents=True)
    runtime = snapshot / 'runtime.json'
    original = b'{"image":"prior-image","model_manifest":null}'
    runtime.write_bytes(original)
    chosen = 'sha256:' + 'a' * 64
    labels = {}

    def command(*arguments):
        if arguments[:2] == ('volume', 'create'):
            key, value = arguments[3].split('=', 1)
            labels[key] = value
            return arguments[-1]
        if arguments[:2] == ('volume', 'inspect'):
            return json.dumps([{'Labels': labels}])
        raise AssertionError('Unexpected external command in metadata-only test')

    monkeypatch.setattr(module, 'command', command)
    monkeypatch.setattr(sys, 'argv', ['full_snapshot.py', operation, '--snapshot', str(snapshot), '--helper-image', chosen])
    module.main()
    assert len(calls) == 1 and calls[0][0] == operation and calls[0][2] == chosen
    assert runtime.read_bytes() == original
    report_path = next((module.ROOT / 'artifacts/community').glob('full-snapshot-*.json'))
    report = json.loads(report_path.read_text(encoding='utf-8'))
    assert report['passed'] is True
    assert report['saved_image'] == 'prior-image' and report['helper_image'] == chosen


@pytest.mark.parametrize('operation,image', [
    ('verify', 'latest'), ('verify', 'sha256:' + 'a' * 63),
    ('verify', 'sha256:' + 'A' * 64), ('verify', '../outside'),
    ('backup', 'sha256:' + 'a' * 64),
])
def test_invalid_or_backup_helper_override_never_calls_docker(snapshot_script, monkeypatch, operation, image):
    module, calls = snapshot_script
    monkeypatch.setattr(sys, 'argv', ['full_snapshot.py', operation, '--helper-image', image])
    with pytest.raises(SystemExit) as error:
        module.main()
    assert error.value.code == 2
    assert calls == []
    assert not module.BACKUPS.exists()
