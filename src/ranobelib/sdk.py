"""Public facade of the SDK: the ``RanobeLib`` class."""

from __future__ import annotations

from types import TracebackType
from typing import Self

from ranobelib.client import ApiClient
from ranobelib.exceptions import VolumeNotFoundError
from ranobelib.models import Chapter, Title, Volume
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

    def __init__(self, url: str) -> None:
        """Initialize the SDK for a title.

        Args:
            url: A ranobelib.me title URL, or a bare ``{id}--{slug}`` identifier.
        """
        self._slug_url = parse_slug_url(url)
        self._client = ApiClient()

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

    async def get_info(self) -> Title:
        """Fetch title metadata: names, cover, summary, genres, tags, authors, teams."""
        data = await self._client.get_title(self._slug_url, fields=_INFO_FIELDS)
        return Title.model_validate(data)

    async def get_table_of_contents(self) -> list[Volume]:
        """Fetch the title's volumes and chapter names/numbers, without chapter content."""
        raw_chapters = await self._client.get_chapters(self._slug_url)
        chapters = [Chapter.model_validate(item) for item in raw_chapters]
        return _group_into_volumes(chapters)

    async def get_chapter(self, volume: int, number: str) -> Chapter:
        """Fetch a single chapter, including its content.

        When a chapter has more than one team's translation, this returns whichever one
        the API picks by default — translation selection is not implemented yet.

        Args:
            volume: The chapter's volume number.
            number: The chapter number, as returned by the API — may contain a decimal
                (e.g. ``"51.6"``).
        """
        data = await self._client.get_chapter(self._slug_url, number=number, volume=str(volume))
        return Chapter.model_validate(data)

    async def get_volume(self, volume: int) -> Volume:
        """Fetch a whole volume: all its chapters, each including content.

        The API has no bulk "volume content" endpoint (see docs/api-notes.md), so this
        fetches the chapter list once to find which numbers belong to the volume, then
        fetches each of those chapters individually and sequentially.

        Args:
            volume: The volume number.

        Raises:
            VolumeNotFoundError: If the title has no chapters for this volume.
        """
        volume_str = str(volume)
        raw_chapters = await self._client.get_chapters(self._slug_url)
        numbers = [item["number"] for item in raw_chapters if item.get("volume") == volume_str]
        if not numbers:
            raise VolumeNotFoundError(self._slug_url, volume=volume_str)

        chapters = []
        for number in numbers:
            data = await self._client.get_chapter(self._slug_url, number=number, volume=volume_str)
            chapters.append(Chapter.model_validate(data))
        return Volume(number=volume_str, chapters=chapters)


def _group_into_volumes(chapters: list[Chapter]) -> list[Volume]:
    """Group a flat, API-ordered chapter list into volumes, preserving that order."""
    grouped: dict[str, list[Chapter]] = {}
    for chapter in chapters:
        grouped.setdefault(chapter.volume, []).append(chapter)
    return [Volume(number=number, chapters=items) for number, items in grouped.items()]
