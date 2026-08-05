"""Disk cache for raw JSON API responses, keyed by request identity."""

from __future__ import annotations

import hashlib
import json
import time
from collections.abc import Callable
from pathlib import Path
from typing import Any

DEFAULT_CACHE_DIR = Path(".ranobelib_cache")
"""Default cache directory, relative to the current working directory."""


class DiskCache:
    """Caches JSON-serializable values to disk, keyed by an arbitrary string.

    One file per key, named by the key's hash (so keys built from slugs, chapter numbers,
    etc. are always safe filenames), holding the cached value plus the time it was written
    so ``ttl`` can be checked on read without touching any other entry. Corrupted or
    unreadable entries are treated as a cache miss rather than raised as an error, since a
    stale/broken cache file shouldn't stop the SDK from just re-fetching the data.
    """

    def __init__(
        self,
        cache_dir: str | Path,
        *,
        ttl: float | None = None,
        clock: Callable[[], float] = time.time,
    ) -> None:
        """Initialize the cache.

        Args:
            cache_dir: Directory to store cache files in. Created lazily on first write.
            ttl: Seconds after which a cache entry is treated as a miss. ``None`` (the
                default) means entries never expire.
            clock: Time source used to stamp and check entries. Overridable for tests.
        """
        self._dir = Path(cache_dir)
        self._ttl = ttl
        self._clock = clock

    def get(self, key: str) -> Any | None:
        """Return the cached value for ``key``, or ``None`` on a miss or expiry."""
        try:
            payload = json.loads(self._path_for(key).read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError, KeyError):
            return None
        if self._ttl is not None and self._clock() - payload["cached_at"] > self._ttl:
            return None
        return payload["data"]

    def set(self, key: str, data: Any) -> None:
        """Write ``data`` to disk under ``key``, creating the cache directory if needed."""
        path = self._path_for(key)
        path.parent.mkdir(parents=True, exist_ok=True)
        payload = {"cached_at": self._clock(), "data": data}
        path.write_text(json.dumps(payload), encoding="utf-8")

    def _path_for(self, key: str) -> Path:
        digest = hashlib.sha256(key.encode("utf-8")).hexdigest()
        return self._dir / f"{digest}.json"
