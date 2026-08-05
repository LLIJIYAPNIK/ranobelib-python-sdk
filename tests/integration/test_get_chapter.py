"""Integration tests for RanobeLib.get_chapter(), backed by VCR cassettes.

These exercise the real api.cdnlibs.org API through the public facade (int volume, str
number). See test_get_chapter_content.py for lower-level ApiClient.get_chapter() coverage
of both chapter-content formats.
"""

import pytest

from ranobelib import ChapterNotFoundError, RanobeLib
from ranobelib.models import Chapter


@pytest.mark.vcr
async def test_get_chapter_returns_chapter_with_content() -> None:
    async with RanobeLib("https://ranobelib.me/ru/book/91443--new-hero-in-dxd") as lib:
        chapter = await lib.get_chapter(volume=1, number="1")

    assert isinstance(chapter, Chapter)
    assert chapter.volume == "1"
    assert chapter.number == "1"
    assert chapter.content is not None
    assert "<p" in chapter.content


@pytest.mark.vcr
async def test_get_chapter_raises_chapter_not_found_for_missing_chapter() -> None:
    async with RanobeLib("https://ranobelib.me/ru/book/91443--new-hero-in-dxd") as lib:
        with pytest.raises(ChapterNotFoundError):
            await lib.get_chapter(volume=999, number="9999")
