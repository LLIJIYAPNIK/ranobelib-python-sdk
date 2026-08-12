"""Catalog listing/search: the ``Catalog`` class.

Unlike ``RanobeLib`` (scoped to one title via its URL/slug), catalog listing isn't scoped to
any title at all — see CLAUDE.md's roadmap entry for why this is a separate entry point with
its own ``ApiClient``/``DiskCache`` rather than a method on ``RanobeLib``.
"""

from __future__ import annotations

from pathlib import Path
from types import TracebackType
from typing import Any, Self

from ranobelib.cache import DEFAULT_CACHE_DIR, DiskCache
from ranobelib.client import RANOBELIB_SITE_ID, ApiClient
from ranobelib.models import CatalogPage, Country, Genre, Title

DEFAULT_SORT = "last_chapter_at"
"""Default sort order: title's last-chapter timestamp — the closest real equivalent to
"recently updated" (the API has no ``updated_at`` sort value, see docs/api-notes.md)."""

MIN_PER_PAGE = 10
MAX_PER_PAGE = 60


class Catalog:
    """Entry point for listing/searching the ranobelib.me catalog.

    Example:
        ```python
        async with Catalog() as catalog:
            page = await catalog.list_titles(query="dxd", genres=[34], status=1)
            for title in page.items:
                print(title.name)
        ```
    """

    def __init__(
        self,
        *,
        cache_dir: str | Path | None = None,
        cache_ttl: float | None = None,
    ) -> None:
        """Initialize the catalog client.

        Args:
            cache_dir: Where to cache raw API responses on disk, one entry per distinct set
                of listing parameters (page/filters/sort) — same disk cache as ``RanobeLib``
                uses (``cache.py``), just keyed by listing parameters instead of a title's
                slug. Defaults to ``.ranobelib_cache`` in the current working directory.
            cache_ttl: Seconds after which a cached page is treated as stale and re-fetched.
                ``None`` (the default) means cached pages never expire on their own — see
                ``refresh=True`` on ``list_titles()`` to force one anyway.
        """
        self._client = ApiClient()
        self._cache = DiskCache(
            cache_dir if cache_dir is not None else DEFAULT_CACHE_DIR, ttl=cache_ttl
        )

    async def __aenter__(self) -> Self:
        return self

    async def __aexit__(
        self,
        exc_type: type[BaseException] | None,
        exc: BaseException | None,
        traceback: TracebackType | None,
    ) -> None:
        await self.aclose()

    async def aclose(self) -> None:
        """Close the underlying HTTP client."""
        await self._client.aclose()

    async def list_titles(
        self,
        *,
        page: int = 1,
        per_page: int = 30,
        query: str | None = None,
        genres: list[int] | None = None,
        tags: list[int] | None = None,
        status: int | None = None,
        country: int | None = None,
        sort: str = DEFAULT_SORT,
        refresh: bool = False,
    ) -> CatalogPage:
        """Fetch one page of catalog listing/search results.

        Args:
            page: 1-based page number.
            per_page: How many titles per page. Must be between ``MIN_PER_PAGE`` (10) and
                ``MAX_PER_PAGE`` (60) — the API's own limits (see docs/api-notes.md);
                anything outside that range raises here instead of a confusing 422 from
                the API.
            query: Free-text search term, matched against name/rus_name/eng_name. ``None``
                (the default) or an empty string lists without searching.
            genres: Genre ids to filter by. A title must have *all* of them, not just one
                (AND, not OR — see docs/api-notes.md). Not validated against ``list_genres()``
                before sending — an unrecognized id just matches nothing rather than erroring.
            tags: ``Tag.id``s (from ``Title.tags``) to filter by. Same AND semantics as
                ``genres`` — a title must have *all* of them, not just any one (confirmed
                against the live API, see docs/api-notes.md; not the OR some might expect
                from tags being more numerous/specific than genres). Also not validated
                before sending, same as ``genres``.
            status: A single ``Title.status.id`` to filter by (e.g. ongoing vs. completed).
            country: A single ``Country.id`` to filter by — a title only has one country of
                origin, unlike ``genres``. Ids come from ``list_countries()``. Sent on the
                wire as the API's ``types[]`` parameter, not a ``country``/``countries[]``
                one — see docs/api-notes.md for why (``Country`` mirrors the API's own
                "type" concept, which isn't strictly limited to literal countries).
            sort: Sort order. Despite the name, this is sent as the API's ``sort_by``
                parameter — an actual ``sort`` parameter exists but is silently ignored by
                the API (see docs/api-notes.md). Known accepted values: ``"name"``,
                ``"created_at"``, ``"views"``, ``"chap_count"``, ``"last_chapter_at"``
                (the default), ``"rate_avg"``, ``"random"`` — this list isn't guaranteed
                exhaustive.
            refresh: Bypass the disk cache and re-fetch from the API even if this exact
                combination of parameters was already cached.

        Returns:
            A ``CatalogPage``: the matching titles (as ``Title`` models) plus whether a next
            page exists.

        Raises:
            ValueError: If ``page`` is less than 1, or ``per_page`` is outside
                ``MIN_PER_PAGE..MAX_PER_PAGE``.
        """
        if page < 1:
            raise ValueError(f"page must be at least 1, got {page}.")
        if not MIN_PER_PAGE <= per_page <= MAX_PER_PAGE:
            raise ValueError(
                f"per_page must be between {MIN_PER_PAGE} and {MAX_PER_PAGE}, got {per_page}."
            )

        key = _cache_key(
            page=page,
            per_page=per_page,
            query=query,
            genres=genres,
            tags=tags,
            status=status,
            country=country,
            sort=sort,
        )
        if not refresh:
            cached = self._cache.get(key)
            if cached is not None:
                return _build_page(cached)

        data = await self._client.list_titles(
            page=page,
            per_page=per_page,
            query=query,
            genres=genres,
            tags=tags,
            status=status,
            country=country,
            sort=sort,
        )
        self._cache.set(key, data)
        return _build_page(data)

    async def list_genres(self, *, refresh: bool = False) -> list[Genre]:
        """Fetch the full list of catalog genres (id → name), for use as filter options
        with ``list_titles(genres=[...])``.

        The underlying endpoint (``GET /api/constants?fields[]=genres``) has no site-scoping
        parameter — it returns the full genre list shared across the whole lib.social
        network in one shot, each tagged with the site ids it applies to (see
        docs/api-notes.md). This filters that down to genres tagged for ranobelib.me before
        returning, so callers don't get filter options (e.g. "Детское") that could never
        match any ranobelib title.

        Args:
            refresh: Bypass the disk cache and re-fetch from the API even if the genre list
                was already cached.

        Returns:
            Every ``Genre`` (id, name, adult flag) that applies to ranobelib.me.
        """
        key = "catalog:genres"
        if not refresh:
            cached = self._cache.get(key)
            if cached is not None:
                return _build_genres(cached)

        data = await self._client.list_genres()
        self._cache.set(key, data)
        return _build_genres(data)

    async def list_countries(self, *, refresh: bool = False) -> list[Country]:
        """Fetch the full list of catalog countries (id → name), for use as filter options
        with ``list_titles(country=...)``.

        Mirrors ``list_genres()`` exactly, down to the network-wide, not-site-scoped shape
        of the underlying endpoint (``GET /api/constants?fields[]=types`` — the API's own
        name for what this SDK calls "country" is "type", see docs/api-notes.md and
        ``Country``'s docstring). This filters that down to entries tagged for ranobelib.me
        before returning, same as ``list_genres()`` does for genres.

        Args:
            refresh: Bypass the disk cache and re-fetch from the API even if the country
                list was already cached.

        Returns:
            Every ``Country`` (id, name) that applies to ranobelib.me.
        """
        key = "catalog:countries"
        if not refresh:
            cached = self._cache.get(key)
            if cached is not None:
                return _build_countries(cached)

        data = await self._client.list_countries()
        self._cache.set(key, data)
        return _build_countries(data)


def _cache_key(
    *,
    page: int,
    per_page: int,
    query: str | None,
    genres: list[int] | None,
    tags: list[int] | None,
    status: int | None,
    country: int | None,
    sort: str,
) -> str:
    genres_part = ",".join(str(genre_id) for genre_id in genres or [])
    tags_part = ",".join(str(tag_id) for tag_id in tags or [])
    return (
        f"catalog:{page}:{per_page}:{query or ''}:{genres_part}:{tags_part}:"
        f"{status}:{country}:{sort}"
    )


def _build_page(data: dict[str, Any]) -> CatalogPage:
    items = [Title.model_validate(item) for item in data["data"]]
    meta = data["meta"]
    return CatalogPage(items=items, page=meta["current_page"], has_next_page=meta["has_next_page"])


def _build_genres(data: list[dict[str, Any]]) -> list[Genre]:
    site_id = int(RANOBELIB_SITE_ID)
    return [Genre.model_validate(item) for item in data if site_id in item.get("site_ids", [])]


def _build_countries(data: list[dict[str, Any]]) -> list[Country]:
    site_id = int(RANOBELIB_SITE_ID)
    return [Country.model_validate(item) for item in data if site_id in item.get("site_ids", [])]
