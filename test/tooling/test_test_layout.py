"""The pytest boundary must not recreate retired root test directories."""
import importlib.util
from pathlib import Path

import pytest

spec = importlib.util.spec_from_file_location(
    "test_runtime_boundary", Path(__file__).resolve().parents[1] / "conftest.py"
)
boundary = importlib.util.module_from_spec(spec)
spec.loader.exec_module(boundary)


@pytest.mark.parametrize("relative", [".backend-test-tmp", ".test-work/run", ".pytest_cache"])
def test_rejects_retired_roots_without_creating_them(relative):
    target = boundary.RUNTIME.parents[2] / relative
    existed = target.exists()
    with pytest.raises(pytest.UsageError, match="test/fixtures/runtime"):
        boundary.require_runtime_child(target)
    assert target.exists() == existed


def test_rejects_runtime_root_and_parent_traversal():
    for path in [boundary.RUNTIME, boundary.RUNTIME / ".." / "outside"]:
        with pytest.raises(pytest.UsageError):
            boundary.require_runtime_child(path)


def test_tmp_path_is_in_the_controlled_runtime(tmp_path):
    assert tmp_path.is_relative_to(boundary.RUNTIME.resolve())
    assert boundary.require_runtime_child(tmp_path) == tmp_path
