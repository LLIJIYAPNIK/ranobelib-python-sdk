"""Disk caching of raw API responses.

Every RanobeLib instance caches raw API responses to disk by default (see cache.py /
"Кэширование" in CLAUDE.md), keyed separately per operation (title metadata, chapter list,
chapter content). This means re-exporting a title in a different format, or re-running a
script during development, doesn't re-hit the network for data already fetched once.
"""

import asyncio
import time

from ranobelib import RanobeLib


async def main() -> None:
    async with RanobeLib(
        # cache_dir defaults to ".ranobelib_cache" in the current directory; passed
        # explicitly here just to make it visible what's being demonstrated.
        "https://ranobelib.me/ru/book/91443--new-hero-in-dxd",
        cache_dir=".ranobelib_cache",
    ) as lib:
        start = time.perf_counter()
        await lib.get_table_of_contents()
        print(f"first call:  {time.perf_counter() - start:.3f}s (hits the API)")

        # Same call again: served entirely from the on-disk cache, no network request.
        start = time.perf_counter()
        await lib.get_table_of_contents()
        print(f"second call: {time.perf_counter() - start:.3f}s (served from disk cache)")

        # refresh=True bypasses the cache for this one call and re-fetches from the API,
        # then updates the cached copy — use it when you know the site's data has changed
        # since it was cached (e.g. new chapters were just released).
        await lib.get_table_of_contents(refresh=True)


asyncio.run(main())

# Expected output (real run against the live site — your exact timings will vary, but the
# gap between the two calls won't):
#
# first call:  0.318s (hits the API)
# second call: 0.001s (served from disk cache)
