"""Catching the SDK's custom exceptions.

All SDK-specific exceptions derive from RanobeLibError (see exceptions.py), so callers who
don't care about the distinction can catch just that base class. This script shows the two
most common ones: TitleNotFoundError (bad/removed title URL) and ChapterNotFoundError (valid
title, but the volume/chapter combination doesn't exist), plus AccessBlockedError — the site's
edge protection rejecting a request outright.

AccessBlockedError vs AuthRequiredError: both come from a 403, but they mean different things
and call for different fixes. AuthRequiredError is the API itself saying "this content needs a
logged-in user" (paid/early-access chapters) — nothing short of authorization helps.
AccessBlockedError is the DDoS-Guard filter in front of the API refusing the request before
the API ever sees it — so far because of missing browser-like headers, which the SDK already
sends. Seeing it in normal use means the site changed its rules (check for an SDK update) or
is blocking your IP (no header change helps then — try the same URL in a browser).

AuthRequiredError and RateLimitError (429 after retries are exhausted) aren't reliably
reproducible in a short standalone script (they need a paywalled title / sustained rate
limiting respectively) — see the API reference for their attributes.
"""

import asyncio

from ranobelib import (
    AccessBlockedError,
    ChapterNotFoundError,
    RanobeLib,
    TitleNotFoundError,
)
from ranobelib.client import ApiClient


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

    # AccessBlockedError, reproduced on purpose. RanobeLib always sends the right headers, so
    # this drops down to the low-level ApiClient (not re-exported from `ranobelib` — it's the
    # layer under RanobeLib/Catalog) and blanks out its Referer: the edge filter rejects
    # requests without a non-empty Referer (see docs/api-notes.md, section "WAF 403"). The
    # same `headers=` override is also the escape hatch in the other direction — sending
    # *newer* headers if the site's rules change before an SDK release catches up.
    async with ApiClient(headers={"Referer": ""}) as client:
        try:
            await client.get_title("91443--new-hero-in-dxd")
        except AccessBlockedError as exc:
            # exc.url is the blocked request; the message spells out what to try next.
            print(exc.url)
            print(exc)


asyncio.run(main())

# Expected output (real run against the live site):
#
# Title not found: '1--this-title-does-not-exist-zzz'
# Chapter not found: '91443--new-hero-in-dxd' volume='999' number='9999'
# https://api.cdnlibs.org/api/manga/91443--new-hero-in-dxd
# Request blocked by the site's protection (not an authorization issue):
# https://api.cdnlibs.org/api/manga/91443--new-hero-in-dxd. The site may have changed which
# requests it accepts: check for an SDK update, or send different headers via
# ranobelib.client.ApiClient(headers=...). If the same URL doesn't open in a browser on this
# network either, the IP itself is blocked and no header change will help.
#
# (The last message is printed as a single line; wrapped here to fit the line length.)
