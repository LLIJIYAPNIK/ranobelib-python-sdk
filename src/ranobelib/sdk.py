"""Public facade of the SDK: the ``RanobeLib`` class."""

from __future__ import annotations

from pathlib import Path
from types import TracebackType
from typing import Any, Self

from ranobelib.cache import DEFAULT_CACHE_DIR, DiskCache
from ranobelib.client import ApiClient
from ranobelib.exceptions import (
    ChapterNotFoundError,
    MultipleTranslationsError,
    VolumeNotFoundError,
)
from ranobelib.exporters import EXPORTERS
from ranobelib.models import Chapter, ChapterBranch, Title, Volume
from ranobelib.numbering import parse_slug_url

_INFO_FIELDS = [
    "background",
    "eng_name",
    "otherNames",
    "summary",
    "releaseDate",
    "genres",
    "tags",
    "teams",
    "authors",
    "artists",
    "chap_count",
]


class RanobeLib:
    """Entry point for interacting with a single ranobelib.me title.

    Example:
        ```python
        async with RanobeLib("https://ranobelib.me/ru/book/6712--high-school-dxd-novel") as lib:
            info = await lib.get_info()
        ```
    """

    def __init__(
        self,
        url: str,
        *,
        cache_dir: str | Path | None = None,
        cache_ttl: float | None = None,
    ) -> None:
        """Initialize the SDK for a title.

        Args:
            url: A ranobelib.me title URL, or a bare ``{id}--{slug}`` identifier.
            cache_dir: Where to cache raw API responses (title metadata, chapter list,
                chapter content) on disk, so a repeated export or downloading newly added
                chapters doesn't re-fetch data already on hand. Defaults to
                ``.ranobelib_cache`` in the current working directory.
            cache_ttl: Seconds after which a cached response is treated as stale and
                re-fetched. ``None`` (the default) means cached responses never expire on
                their own — see ``refresh=True`` on individual methods to force one anyway.
        """
        self._slug_url = parse_slug_url(url)
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

    async def get_info(self, *, refresh: bool = False) -> Title:
        """Fetch title metadata: names, cover, summary, genres, tags, authors, teams.

        Args:
            refresh: Bypass the disk cache and re-fetch from the API even if a cached
                response is on hand.
        """
        data = await self._get_title(refresh=refresh)
        return Title.model_validate(data)

    async def get_table_of_contents(self, *, refresh: bool = False) -> list[Volume]:
        """Fetch the title's volumes and chapter names/numbers, without chapter content.

        Args:
            refresh: Bypass the disk cache and re-fetch from the API even if a cached
                response is on hand — needed to pick up newly published chapters, since
                otherwise the cached chapter list would keep being reused.
        """
        raw_chapters = await self._get_chapters(refresh=refresh)
        chapters = [Chapter.model_validate(item) for item in raw_chapters]
        return _group_into_volumes(chapters)

    async def get_chapter(
        self,
        volume: int,
        number: str,
        *,
        branch_id: int | None = None,
        refresh: bool = False,
    ) -> Chapter:
        """Fetch a single chapter, including its content.

        When a chapter has more than one team's translation and ``branch_id`` isn't given,
        this raises ``MultipleTranslationsError`` rather than guessing — see
        ``get_translations()`` and docs/api-notes.md for why the API's own default (when
        ``branch_id`` is omitted) isn't relied on. Doing this check costs an extra request
        to fetch the chapter list, only when ``branch_id`` isn't already given.

        Args:
            volume: The chapter's volume number.
            number: The chapter number, as returned by the API — may contain a decimal
                (e.g. ``"51.6"``).
            branch_id: Which translation to fetch, as returned by ``get_translations()``.
                Only required when the chapter has more than one.
            refresh: Bypass the disk cache and re-fetch from the API even if a cached
                response is on hand.

        Raises:
            MultipleTranslationsError: If the chapter has more than one translation and
                ``branch_id`` wasn't given.
        """
        volume_str = str(volume)
        if branch_id is None:
            raw_chapters = await self._get_chapters(refresh=refresh)
            branch_id = self._resolve_branch_id(volume_str, number, raw_chapters)
        return await self._fetch_chapter(volume_str, number, branch_id, refresh=refresh)

    async def get_chapters(self, chapters: list[tuple[int, str]]) -> list[Chapter]:
        """Fetch several chapters, including their content.

        Fetches the chapter list once, shared across all requested chapters (also used to
        detect chapters with more than one translation — see ``get_chapter``), then each
        chapter individually and sequentially, in the order given.

        Args:
            chapters: A list of ``(volume, number)`` pairs identifying each chapter.

        Raises:
            ChapterNotFoundError: If any requested chapter doesn't exist.
            MultipleTranslationsError: If any requested chapter has more than one
                translation.
        """
        raw_chapters = await self._get_chapters()
        result = []
        for volume, number in chapters:
            volume_str = str(volume)
            branch_id = self._resolve_branch_id(volume_str, number, raw_chapters)
            result.append(await self._fetch_chapter(volume_str, number, branch_id))
        return result

    async def get_translations(self, volume: int, number: str) -> list[ChapterBranch]:
        """Fetch the available translations (branches) for a chapter.

        Args:
            volume: The chapter's volume number.
            number: The chapter number.

        Raises:
            ChapterNotFoundError: If no chapter exists for this volume/number.
        """
        volume_str = str(volume)
        raw_chapters = await self._get_chapters()
        item = _find_raw_chapter(raw_chapters, volume_str, number)
        if item is None:
            raise ChapterNotFoundError(self._slug_url, volume=volume_str, number=number)
        return [ChapterBranch.model_validate(branch) for branch in item.get("branches") or []]

    async def get_volume(self, volume: int) -> Volume:
        """Fetch a whole volume: all its chapters, each including content.

        The API has no bulk "volume content" endpoint (see docs/api-notes.md), so this
        fetches the chapter list once to find which numbers belong to the volume, then
        fetches each of those chapters individually and sequentially.

        Args:
            volume: The volume number.

        Raises:
            VolumeNotFoundError: If the title has no chapters for this volume.
            MultipleTranslationsError: If any of the volume's chapters has more than one
                translation.
        """
        raw_chapters = await self._get_chapters()
        return await self._build_volume(volume, raw_chapters)

    async def get_volumes(self, volumes: list[int]) -> list[Volume]:
        """Fetch several whole volumes, each including chapter content.

        Fetches the chapter list once, shared across all requested volumes, then each
        chapter individually and sequentially — same approach as ``get_volume``, applied
        to more than one volume without re-fetching the chapter list per volume.

        Args:
            volumes: The volume numbers to fetch.

        Raises:
            VolumeNotFoundError: If the title has no chapters for one of the volumes.
            MultipleTranslationsError: If any of the volumes' chapters has more than one
                translation.
        """
        raw_chapters = await self._get_chapters()
        return [await self._build_volume(volume, raw_chapters) for volume in volumes]

    async def export(self, chapters: list[Chapter], *, fmt: str, path: str | Path) -> Path:
        """Export chapters to a file.

        Args:
            chapters: The chapters to include, in the order they should appear.
            path: Where to write the exported file.
            fmt: Export format — a key of ``ranobelib.exporters.EXPORTERS``
                (currently: ``"txt"``).

        Raises:
            ValueError: If ``fmt`` isn't a registered export format.
        """
        exporter_cls = EXPORTERS.get(fmt)
        if exporter_cls is None:
            available = ", ".join(sorted(EXPORTERS)) or "(none registered)"
            raise ValueError(f"Unknown export format {fmt!r}. Available: {available}")
        title = await self.get_info()
        return exporter_cls().export(title, chapters, Path(path))

    async def _build_volume(self, volume: int, raw_chapters: list[dict[str, Any]]) -> Volume:
        volume_str = str(volume)
        numbers = [item["number"] for item in raw_chapters if item.get("volume") == volume_str]
        if not numbers:
            raise VolumeNotFoundError(self._slug_url, volume=volume_str)

        chapters = []
        for number in numbers:
            branch_id = self._resolve_branch_id(volume_str, number, raw_chapters)
            chapters.append(await self._fetch_chapter(volume_str, number, branch_id))
        return Volume(number=volume_str, chapters=chapters)

    async def _get_title(self, *, refresh: bool = False) -> dict[str, Any]:
        key = f"title:{self._slug_url}:{','.join(sorted(_INFO_FIELDS))}"
        if not refresh:
            cached = self._cache.get(key)
            if cached is not None:
                return cached  # type: ignore[no-any-return]
        data = await self._client.get_title(self._slug_url, fields=_INFO_FIELDS)
        self._cache.set(key, data)
        return data

    async def _get_chapters(self, *, refresh: bool = False) -> list[dict[str, Any]]:
        key = f"chapters:{self._slug_url}"
        if not refresh:
            cached = self._cache.get(key)
            if cached is not None:
                return cached  # type: ignore[no-any-return]
        data = await self._client.get_chapters(self._slug_url)
        self._cache.set(key, data)
        return data

    async def _fetch_chapter(
        self, volume_str: str, number: str, branch_id: int | None, *, refresh: bool = False
    ) -> Chapter:
        key = f"chapter:{self._slug_url}:{volume_str}:{number}:{branch_id}"
        if not refresh:
            cached = self._cache.get(key)
            if cached is not None:
                return Chapter.model_validate(cached)
        data = await self._client.get_chapter(
            self._slug_url, number=number, volume=volume_str, branch_id=branch_id
        )
        self._cache.set(key, data)
        return Chapter.model_validate(data)

    def _resolve_branch_id(
        self, volume_str: str, number: str, raw_chapters: list[dict[str, Any]]
    ) -> int | None:
        item = _find_raw_chapter(raw_chapters, volume_str, number)
        if item is None:
            return None  # Let the chapter fetch itself raise ChapterNotFoundError.

        branches = item.get("branches") or []
        if len(branches) <= 1:
            return None

        raise MultipleTranslationsError(
            self._slug_url,
            volume=volume_str,
            number=number,
            branches=[ChapterBranch.model_validate(branch) for branch in branches],
        )


def _group_into_volumes(chapters: list[Chapter]) -> list[Volume]:
    """Group a flat, API-ordered chapter list into volumes, preserving that order."""
    grouped: dict[str, list[Chapter]] = {}
    for chapter in chapters:
        grouped.setdefault(chapter.volume, []).append(chapter)
    return [Volume(number=number, chapters=items) for number, items in grouped.items()]


def _find_raw_chapter(
    raw_chapters: list[dict[str, Any]], volume_str: str, number: str
) -> dict[str, Any] | None:
    """Find a chapter-list entry by volume/number, or ``None`` if there isn't one."""
    return next(
        (
            item
            for item in raw_chapters
            if item.get("volume") == volume_str and item.get("number") == number
        ),
        None,
    )
