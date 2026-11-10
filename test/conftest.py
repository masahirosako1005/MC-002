"""Keep disposable pytest data inside the project's test workspace."""
from pathlib import Path

import pytest

RUNTIME = Path(__file__).absolute().parent / "fixtures" / "runtime"


def require_runtime_child(path: Path) -> Path:
    """Reject broad roots and paths redirected outside the runtime directory."""
    root = RUNTIME.resolve()
    target = path.resolve()
    if root != RUNTIME or target == root or not target.is_relative_to(root):
        raise pytest.UsageError(
            "Test temporary data must use a child of test/fixtures/runtime. "
            "Use test/run.py or --basetemp=test/fixtures/runtime/<run-name>."
        )
    return target


@pytest.hookimpl(tryfirst=True)
def pytest_configure(config: pytest.Config) -> None:
    # Run before tmp_path/cache initialize or clear their writable directories.
    base = config.option.basetemp
    config.option.basetemp = str(
        require_runtime_child(Path(base) if base else RUNTIME / "pytest-current")
    )
    cache = Path(config.getini("cache_dir"))
    require_runtime_child(cache if cache.is_absolute() else config.rootpath / cache)
