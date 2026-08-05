"""Unit tests for ranobelib.cache.DiskCache."""

from pathlib import Path

from ranobelib.cache import DiskCache


def test_get_returns_none_for_missing_key(tmp_path: Path) -> None:
    cache = DiskCache(tmp_path)

    assert cache.get("missing") is None


def test_set_then_get_roundtrips_value(tmp_path: Path) -> None:
    cache = DiskCache(tmp_path)

    cache.set("key", {"id": 1, "name": "Example"})

    assert cache.get("key") == {"id": 1, "name": "Example"}


def test_set_creates_cache_directory(tmp_path: Path) -> None:
    cache_dir = tmp_path / "nested" / "cache"
    cache = DiskCache(cache_dir)

    cache.set("key", [1, 2, 3])

    assert cache_dir.exists()
    assert cache.get("key") == [1, 2, 3]


def test_get_returns_value_before_ttl_expires(tmp_path: Path) -> None:
    clock = _FakeClock(start=1000.0)
    cache = DiskCache(tmp_path, ttl=60, clock=clock)

    cache.set("key", "value")
    clock.advance(59)

    assert cache.get("key") == "value"


def test_get_returns_none_after_ttl_expires(tmp_path: Path) -> None:
    clock = _FakeClock(start=1000.0)
    cache = DiskCache(tmp_path, ttl=60, clock=clock)

    cache.set("key", "value")
    clock.advance(61)

    assert cache.get("key") is None


def test_get_never_expires_without_ttl(tmp_path: Path) -> None:
    clock = _FakeClock(start=1000.0)
    cache = DiskCache(tmp_path, ttl=None, clock=clock)

    cache.set("key", "value")
    clock.advance(10_000_000)

    assert cache.get("key") == "value"


def test_get_treats_corrupted_cache_file_as_a_miss(tmp_path: Path) -> None:
    cache = DiskCache(tmp_path)
    cache.set("key", "value")

    for path in tmp_path.iterdir():
        path.write_text("not json", encoding="utf-8")

    assert cache.get("key") is None


def test_different_keys_do_not_collide(tmp_path: Path) -> None:
    cache = DiskCache(tmp_path)

    cache.set("a", "value-a")
    cache.set("b", "value-b")

    assert cache.get("a") == "value-a"
    assert cache.get("b") == "value-b"


class _FakeClock:
    def __init__(self, *, start: float) -> None:
        self._now = start

    def advance(self, seconds: float) -> None:
        self._now += seconds

    def __call__(self) -> float:
        return self._now
