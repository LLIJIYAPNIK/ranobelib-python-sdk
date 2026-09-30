"""HTTP settings shared by every client the SDK opens (not public API).

Lives in its own module rather than in ``client.py`` because it isn't specific to the
api.cdnlibs.org JSON API: the exporters' image-downloading clients (cover.cdnlibs.org,
ranobelib.me uploads) need the same headers, and importing them from here keeps the
exporters from depending on ``ApiClient``'s module just for a constant.
"""

from __future__ import annotations

SITE_ORIGIN = "https://ranobelib.me"
"""Origin of the ranobelib.me website, as its own pages send it."""

BROWSER_HEADERS: dict[str, str] = {
    "Origin": SITE_ORIGIN,
    "Referer": f"{SITE_ORIGIN}/",
    "User-Agent": (
        "Mozilla/5.0 (iPhone; CPU iPhone OS 18_5 like Mac OS X) AppleWebKit/605.1.15 "
        "(KHTML, like Gecko) Version/18.5 Mobile/15E148 Safari/604.1"
    ),
}
"""Headers a browser on ranobelib.me sends, so requests look like they come from the site.

The DDoS-Guard edge in front of api.cdnlibs.org and cover.cdnlibs.org rejects requests
without a ranobelib.me ``Referer`` with an HTML 403 page (see docs/api-notes.md, section
"WAF 403"). ``Referer`` alone was enough when checked; ``Origin`` and a real browser
``User-Agent`` are sent too so the request as a whole matches what the site itself sends,
rather than advertising ``python-httpx``.
"""
