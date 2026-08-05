"""EPUB exporter (cover and in-chapter illustrations included)."""

from __future__ import annotations

import asyncio
import html
from html.parser import HTMLParser
from pathlib import Path
from typing import ClassVar
from urllib.parse import urlsplit

import httpx
from ebooklib import epub

from ranobelib.exporters import register
from ranobelib.exporters._shared import chapter_heading
from ranobelib.models import Chapter, Cover, Title

_VOID_TAGS = frozenset({"br", "hr", "img"})

_MEDIA_TYPES = {
    ".jpg": "image/jpeg",
    ".jpeg": "image/jpeg",
    ".png": "image/png",
    ".gif": "image/gif",
    ".webp": "image/webp",
}
_DEFAULT_EXTENSION = ".jpg"

_IMAGE_CONCURRENCY = 5
"""Same conservative default as ApiClient's max_concurrency (see client.py) — these are a
different host (site/CDN uploads, not api.cdnlibs.org) with unknown rate limits of their
own, so this doesn't reuse ApiClient's own semaphore/retry machinery, just a plain cap.
A failed download is skipped rather than retried: embedding is best-effort, one broken
image shouldn't fail the whole export (see EpubExporter.export)."""


class _ImageUrlCollector(HTMLParser):
    """Collects every ``<img src="...">`` URL referenced in a chapter-content HTML fragment."""

    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self.urls: list[str] = []

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        if tag == "img":
            src = dict(attrs).get("src")
            if src:
                self.urls.append(src)

    handle_startendtag = handle_starttag


def extract_image_urls(html_fragment: str) -> list[str]:
    """List the ``<img src="...">`` URLs referenced in a chapter-content HTML fragment."""
    collector = _ImageUrlCollector()
    collector.feed(html_fragment)
    return collector.urls


class _ImageSrcRewriter(HTMLParser):
    """Re-emits chapter-content HTML with ``<img src="...">`` URLs replaced per a mapping.

    Rebuilds the markup tag-by-tag (rather than a targeted regex substitution) for the same
    reason the txt/fb2 exporters use ``HTMLParser`` over regex: HTML-string-format chapters
    pass the site's own markup through as-is (see docs/api-notes.md). Everything other than
    ``img`` passes through unchanged; ebooklib re-parses the result leniently via
    ``lxml.html``, so this doesn't need to produce strict XHTML.

    An ``<img>`` whose URL isn't in ``url_to_local`` (download failed or was never
    attempted) is dropped entirely rather than kept pointing at the original external URL —
    a dangling absolute-URL reference isn't a self-contained embed, just a broken-looking
    image in most readers, so "not embedded" reads as "not present" instead.
    """

    def __init__(self, url_to_local: dict[str, str]) -> None:
        super().__init__(convert_charrefs=True)
        self._url_to_local = url_to_local
        self._output: list[str] = []

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        self._emit(tag, attrs, self_closing=tag in _VOID_TAGS)

    def handle_startendtag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        self._emit(tag, attrs, self_closing=True)

    def _emit(self, tag: str, attrs: list[tuple[str, str | None]], *, self_closing: bool) -> None:
        if tag == "img":
            local_src = self._url_to_local.get(dict(attrs).get("src") or "")
            if local_src is None:
                return
            attrs = [(name, local_src if name == "src" else value) for name, value in attrs]

        parts = [f"<{tag}"]
        for name, value in attrs:
            if value is None:
                parts.append(f" {name}")
            else:
                parts.append(f' {name}="{html.escape(value, quote=True)}"')
        parts.append(" />" if self_closing else ">")
        self._output.append("".join(parts))

    def handle_endtag(self, tag: str) -> None:
        if tag not in _VOID_TAGS:
            self._output.append(f"</{tag}>")

    def handle_data(self, data: str) -> None:
        self._output.append(html.escape(data))

    def get_html(self) -> str:
        return "".join(self._output)


def rewrite_image_srcs(html_fragment: str, url_to_local: dict[str, str]) -> str:
    """Rewrite ``<img src="...">`` URLs in ``html_fragment`` per ``url_to_local``."""
    rewriter = _ImageSrcRewriter(url_to_local)
    rewriter.feed(html_fragment)
    return rewriter.get_html()


def _pick_cover_url(cover: Cover) -> str | None:
    return cover.default or cover.md or cover.thumbnail


def _guess_extension(url: str) -> str:
    suffix = Path(urlsplit(url).path).suffix.lower()
    return suffix if suffix in _MEDIA_TYPES else _DEFAULT_EXTENSION


def _media_type_for(extension: str) -> str:
    return _MEDIA_TYPES.get(extension, _MEDIA_TYPES[_DEFAULT_EXTENSION])


async def _try_download(
    client: httpx.AsyncClient, semaphore: asyncio.Semaphore, url: str
) -> bytes | None:
    async with semaphore:
        try:
            response = await client.get(url)
            response.raise_for_status()
        except httpx.HTTPError:
            return None
    return response.content


@register
class EpubExporter:
    """Exports chapters as a single EPUB file, with cover and in-chapter illustrations."""

    format: ClassVar[str] = "epub"

    def __init__(self, *, transport: httpx.AsyncBaseTransport | None = None) -> None:
        """Initialize the exporter.

        Args:
            transport: Custom ``httpx`` transport for the image-downloading client, e.g. a
                mock transport for tests. Not part of the ``Exporter`` protocol itself —
                ``RanobeLib.export()`` always constructs exporters with no arguments, so
                this is only reachable by instantiating ``EpubExporter`` directly.
        """
        self._transport = transport

    async def export(self, title: Title, chapters: list[Chapter], output_path: Path) -> Path:
        """Write ``chapters`` to ``output_path`` as an EPUB file.

        Downloads the title's cover and every image referenced in the chapters' content and
        embeds them; a download that fails is skipped rather than failing the whole export
        (see docs/api-notes.md's "Illustrations" notes).

        Args:
            title: The chapters' parent title; supplies metadata, cover, and authors.
            chapters: The chapters to include, in the order they should appear.
            output_path: Where to write the ``.epub`` file.

        Returns:
            ``output_path``.
        """
        book = epub.EpubBook()
        book.set_identifier(title.slug_url)
        book.set_title(title.name)
        book.set_language("ru")
        for author in title.authors:
            book.add_author(author.name)

        semaphore = asyncio.Semaphore(_IMAGE_CONCURRENCY)
        async with httpx.AsyncClient(
            timeout=15.0, follow_redirects=True, transport=self._transport
        ) as client:
            cover_url = _pick_cover_url(title.cover)
            if cover_url is not None:
                cover_bytes = await _try_download(client, semaphore, cover_url)
                if cover_bytes is not None:
                    book.set_cover(f"cover{_guess_extension(cover_url)}", cover_bytes)

            image_urls = list(
                dict.fromkeys(
                    url for chapter in chapters for url in extract_image_urls(chapter.content or "")
                )
            )
            downloads = await asyncio.gather(
                *(_try_download(client, semaphore, url) for url in image_urls)
            )

        url_to_local: dict[str, str] = {}
        for index, (url, data) in enumerate(zip(image_urls, downloads, strict=True), start=1):
            if data is None:
                continue
            extension = _guess_extension(url)
            local_name = f"images/img{index:04d}{extension}"
            url_to_local[url] = local_name
            book.add_item(
                epub.EpubItem(
                    uid=local_name,
                    file_name=local_name,
                    media_type=_media_type_for(extension),
                    content=data,
                )
            )

        spine: list[object] = ["nav"]
        toc: list[object] = []
        for index, chapter in enumerate(chapters, start=1):
            heading = chapter_heading(chapter)
            body = rewrite_image_srcs(chapter.content or "", url_to_local)
            doc = epub.EpubHtml(
                uid=f"chapter_{index}",
                file_name=f"chapter_{index}.xhtml",
                title=heading,
                lang="ru",
            )
            doc.content = f"<h1>{html.escape(heading)}</h1>{body}"
            book.add_item(doc)
            spine.append(doc)
            toc.append(doc)

        book.toc = toc
        book.add_item(epub.EpubNcx())
        book.add_item(epub.EpubNav())
        book.spine = spine

        epub.write_epub(str(output_path), book)
        return output_path
