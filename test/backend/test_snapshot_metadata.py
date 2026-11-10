"""Backup metadata compatibility only; no Docker or live data operations."""
import importlib.util
import json
import sys
from pathlib import Path

import pytest


@pytest.fixture
def snapshot_script(tmp_path, monkeypatch):
    path = Path(__file__).resolve().parents[2] / 'community/scripts/full_snapshot.py'
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
