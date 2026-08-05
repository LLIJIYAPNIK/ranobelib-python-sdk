"""Integration tests for RanobeLib.get_chapters(), backed by VCR cassettes.

These exercise the real api.cdnlibs.org API through the public facade: one request per
requested chapter, same as calling get_chapter() in a loop (see get_volume, which does the
same thing for a whole volume).
"""

import pytest

from ranobelib import ChapterNotFoundError, RanobeLib
from ranobelib.models import Chapter


@pytest.mark.vcr
async def test_get_chapters_returns_chapters_in_requested_order() -> None:
    async with RanobeLib("https://ranobelib.me/ru/book/91443--new-hero-in-dxd") as lib:
        chapters = await lib.get_chapters([(1, "2"), (0, "1")])

    assert len(chapters) == 2
    assert all(isinstance(chapter, Chapter) for chapter in chapters)
    assert (chapters[0].volume, chapters[0].number) == ("1", "2")
    assert (chapters[1].volume, chapters[1].number) == ("0", "1")
    assert all(chapter.content is not None for chapter in chapters)


@pytest.mark.vcr
async def test_get_chapters_raises_chapter_not_found_for_missing_chapter() -> None:
    async with RanobeLib("https://ranobelib.me/ru/book/91443--new-hero-in-dxd") as lib:
        with pytest.raises(ChapterNotFoundError):
            await lib.get_chapters([(1, "2"), (999, "9999")])
