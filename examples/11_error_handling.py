"""Catching the SDK's custom exceptions.

All SDK-specific exceptions derive from RanobeLibError (see exceptions.py), so callers who
don't care about the distinction can catch just that base class. This script shows the two
most common ones: TitleNotFoundError (bad/removed title URL) and ChapterNotFoundError (valid
title, but the volume/chapter combination doesn't exist).

AuthRequiredError (403, paid/early-access content) and RateLimitError (429 after retries are
exhausted) follow the same pattern but aren't reliably reproducible in a short standalone
script (they need a paywalled title / sustained rate limiting respectively) — see the API
reference for their attributes.
"""

import asyncio

from ranobelib import ChapterNotFoundError, RanobeLib, TitleNotFoundError


async def main() -> None:
    # A URL shaped like a valid title page, but for a title id that doesn't exist.
    async with RanobeLib("https://ranobelib.me/ru/book/1--this-title-does-not-exist-zzz") as lib:
        try:
            await lib.get_info()
        except TitleNotFoundError as exc:
            print(exc)

    # A real title, but a volume/chapter combination it doesn't have.
    async with RanobeLib("https://ranobelib.me/ru/book/91443--new-hero-in-dxd") as lib:
        try:
            await lib.get_chapter(volume=999, number="9999")
        except ChapterNotFoundError as exc:
            print(exc)


asyncio.run(main())

# Expected output (real run against the live site):
#
# Title not found: '1--this-title-does-not-exist-zzz'
# Chapter not found: '91443--new-hero-in-dxd' volume='999' number='9999'
