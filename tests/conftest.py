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
