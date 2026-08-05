"""Shared pytest fixtures."""

from pathlib import Path
from typing import Any

import pytest

CASSETTE_DIR = Path(__file__).parent / "cassettes"


@pytest.fixture(scope="module")
def vcr_cassette_dir() -> str:
    return str(CASSETTE_DIR)


@pytest.fixture(scope="module")
def vcr_config() -> dict[str, Any]:
    return {"record_mode": "once"}


@pytest.fixture(autouse=True)
def _isolated_disk_cache(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """Point RanobeLib's default cache_dir at a per-test tmp_path.

    Without this, every ``RanobeLib(url)`` call in the test suite (the vast majority don't
    pass ``cache_dir`` explicitly) would share one real ``.ranobelib_cache/`` directory
    under the repo root across test runs — polluting the repo and letting cached responses
    from a previous run silently replace what a cassette is supposed to be verifying.
    """
    monkeypatch.setattr("ranobelib.sdk.DEFAULT_CACHE_DIR", tmp_path / ".ranobelib_cache")
