# ranobelib-python-sdk

[![PyPI](https://img.shields.io/pypi/v/ranobelib-python-sdk)](https://pypi.org/project/ranobelib-python-sdk/)
[![License: MIT](https://img.shields.io/github/license/LLIJIYAPNIK/ranobelib-python-sdk)](LICENSE)
[![Python versions](https://img.shields.io/badge/python-3.11%20%7C%203.12%20%7C%203.13-blue)](pyproject.toml)
[![CI](https://github.com/LLIJIYAPNIK/ranobelib-python-sdk/actions/workflows/ci.yml/badge.svg)](https://github.com/LLIJIYAPNIK/ranobelib-python-sdk/actions/workflows/ci.yml)
[![Coverage Status](https://coveralls.io/repos/github/LLIJIYAPNIK/ranobelib-python-sdk/badge.svg?branch=main)](https://coveralls.io/github/LLIJIYAPNIK/ranobelib-python-sdk?branch=main)
[![Docs](https://github.com/LLIJIYAPNIK/ranobelib-python-sdk/actions/workflows/docs.yml/badge.svg)](https://github.com/LLIJIYAPNIK/ranobelib-python-sdk/actions/workflows/docs.yml)

Async Python SDK for [ranobelib.me](https://ranobelib.me): fetch title metadata, download
chapters and volumes, and export to epub, fb2, txt, or pdf.

The SDK talks to the undocumented but open JSON API behind the site (`api.cdnlibs.org`,
part of the lib.social network) instead of scraping HTML.

> **Status:** all the calls in the quickstart below are implemented — metadata, table of
> contents, single/bulk chapter and volume downloads, whole-title bulk download, translation
> selection, and export to
> `"txt"`, `"fb2"`, `"epub"`, or `"pdf"` (cover + in-chapter illustrations embedded in
> epub/pdf). Raw API responses are cached to disk, and the underlying client bounds
> concurrency, paces requests, and retries 429/5xx with backoff. `fmt="pdf"` needs
> WeasyPrint's native dependencies (Pango/cairo/GTK3) installed on the system — `pip
> install`/`uv add` alone doesn't guarantee that on every platform; without them,
> `export(fmt="pdf")` raises the same "unknown format" error the other three formats don't.
> Authorization (private/18+/paid content) is out of scope — see `CLAUDE.md` for the full
> architecture and design decisions behind all of this.

## Installation

```bash
uv add ranobelib-python-sdk
```

or

```bash
pip install ranobelib-python-sdk
```

Requires Python 3.11+.

## Quickstart

```python
from ranobelib import RanobeLib

async with RanobeLib("https://ranobelib.me/ru/book/6712--high-school-dxd-novel") as lib:
    info = await lib.get_info()
    toc = await lib.get_table_of_contents()

    chapter = await lib.get_chapter(volume=6, number="51.6")
    volume = await lib.get_volume(volume=6)

    chapters = await lib.get_chapters([(6, "51.6"), (6, "52")])
    volumes = await lib.get_volumes([1, 2, 3])

    translations = await lib.get_translations(volume=6, number="51.6")
    chapter = await lib.get_chapter(volume=6, number="51.6", branch_id=...)

    all_volumes = await lib.download_title(translation_index=0, chapter_delay=0.5)

    await lib.export(chapters, fmt="epub", path="output.epub")
```

This is the full current public API — everything above is implemented and works today.

## Examples

Every snippet below is a complete, self-contained script — save it as `example.py` and run
`python example.py`. Each one really was run against the live site to produce the "Result"
shown; only chapter content is truncated with `[:200]`/`[:300]` for readability, everything
else is the real output verbatim.

### Title metadata

```python
import asyncio

from ranobelib import RanobeLib


async def main() -> None:
    async with RanobeLib("https://ranobelib.me/ru/book/6712--high-school-dxd-novel") as lib:
        info = await lib.get_info()
        print(info.name)
        print(info.rus_name)
        print(info.status.label)
        print(info.chapter_count)
        print([genre.name for genre in info.genres[:5]])


asyncio.run(main())
```

**Result:**

```
Haisukuru Di Di (Novel)
Старшая школа D×D (Новелла)
Завершён
308
['Боевик', 'Боевые искусства', 'Вампиры', 'Гарем', 'Драма']
```

### Table of contents

```python
import asyncio

from ranobelib import RanobeLib


async def main() -> None:
    async with RanobeLib("https://ranobelib.me/ru/book/91443--new-hero-in-dxd") as lib:
        volumes = await lib.get_table_of_contents()
        for volume in volumes:
            print(f"Volume {volume.number}: {len(volume.chapters)} chapters")
        print(volumes[0].chapters[0].name)


asyncio.run(main())
```

**Result:**

```
Volume 0: 1 chapters
Volume 1: 46 chapters
(НЕ ГОТОВО) Возможный гарем
```

### A single chapter

```python
import asyncio

from ranobelib import RanobeLib


async def main() -> None:
    async with RanobeLib("https://ranobelib.me/ru/book/91443--new-hero-in-dxd") as lib:
        chapter = await lib.get_chapter(volume=1, number="1")
        print(chapter.name)
        print(chapter.content[:200])


asyncio.run(main())
```

**Result:**

```
Глава 1
<p data-paragraph-index="1">"Наконец, я наконец-то могу вернуться." - говорю я с широкой
улыбкой на лице, хотя по моим щекам текут слезы. Прошло слишком много времени с тех пор,
как я застрял в этом м
```

### Several chapters at once

```python
import asyncio

from ranobelib import RanobeLib


async def main() -> None:
    async with RanobeLib("https://ranobelib.me/ru/book/91443--new-hero-in-dxd") as lib:
        chapters = await lib.get_chapters([(1, "1"), (1, "2")])
        for chapter in chapters:
            print(chapter.volume, chapter.number, len(chapter.content))


asyncio.run(main())
```

**Result:**

```
1 1 30722
1 2 22747
```

### A whole volume

```python
import asyncio

from ranobelib import RanobeLib


async def main() -> None:
    async with RanobeLib("https://ranobelib.me/ru/book/91443--new-hero-in-dxd") as lib:
        volume = await lib.get_volume(0)
        print(volume.number, [chapter.number for chapter in volume.chapters])


asyncio.run(main())
```

**Result:**

```
0 ['1']
```

### Several volumes at once

```python
import asyncio

from ranobelib import RanobeLib


async def main() -> None:
    async with RanobeLib("https://ranobelib.me/ru/book/91443--new-hero-in-dxd") as lib:
        volumes = await lib.get_volumes([0, 1])
        for volume in volumes:
            print(volume.number, len(volume.chapters))


asyncio.run(main())
```

**Result:**

```
0 1
1 46
```

### Selecting a translation

`11407--solo-leveling` has two competing translations of its prologue. `get_chapter()`
refuses to guess which one you want — it raises `MultipleTranslationsError` instead —
unless `branch_id` is given explicitly, so you list the options with `get_translations()`
first:

```python
import asyncio

from ranobelib import MultipleTranslationsError, RanobeLib


async def main() -> None:
    async with RanobeLib("https://ranobelib.me/ru/book/11407--solo-leveling") as lib:
        branches = await lib.get_translations(volume=1, number="0")
        for branch in branches:
            print(branch.branch_id, [team.name for team in branch.teams])

        try:
            await lib.get_chapter(volume=1, number="0")
        except MultipleTranslationsError as exc:
            print("ambiguous, pick one:", [b.branch_id for b in exc.branches])

        chapter = await lib.get_chapter(volume=1, number="0", branch_id=branches[0].branch_id)
        print(chapter.content[:60])


asyncio.run(main())
```

**Result:**

```
2251 ['BerkuD13']
635 ['Неизвестный']
ambiguous, pick one: [2251, 635]
<p data-paragraph-index="1">Прокачка уровня в одиночку</p><p data-paragraph-index="2">0 . Пролог</p
```

### Downloading a whole title

`download_title()` fetches every chapter of a title in one call. When a title has chapters
with more than one translation, it raises `MultipleTitleTranslationsError` listing *all* of
them up front (not just the first one hit) — pass `branch_id` or `translation_index` to
resolve them:

```python
import asyncio

from ranobelib import MultipleTitleTranslationsError, RanobeLib


async def main() -> None:
    async with RanobeLib("https://ranobelib.me/ru/book/40195--enbizaka-no-shitateya") as lib:
        volumes = await lib.download_title(chapter_delay=0.5)
        for volume in volumes:
            print(volume.number, [chapter.number for chapter in volume.chapters])

    slug = "113306--bungou-stray-dogs-gaiden-ayatsuji-yukito-vs-kyogoku-natsuhiko"
    async with RanobeLib(f"https://ranobelib.me/ru/book/{slug}") as lib:
        try:
            await lib.download_title()
        except MultipleTitleTranslationsError as exc:
            print(f"{len(exc.chapters)} ambiguous chapter(s):")
            for chapter in exc.chapters:
                print(" ", chapter.volume, chapter.number, [b.branch_id for b in chapter.branches])

        volumes = await lib.download_title(translation_index=0)
        print([chapter.number for chapter in volumes[0].chapters])


asyncio.run(main())
```

**Result:**

```
1 ['0', '1']
3 ambiguous chapter(s):
  1 0 [12954, 12955]
  1 1 [12955, 12954]
  1 2 [12954, 12955]
['0', '1', '2', '3', '4', '5']
```

Note chapter `1`'s branches are listed in the opposite order from chapters `0`/`2` —
`translation_index=0` resolves by each chapter's own branch order, not a shared `branch_id`,
which is why it picks a different team for chapter `1` than for `0`/`2` here. Use `branch_id`
instead when you know the specific translation you want and it's shared across chapters.

### Disk caching

Raw API responses are cached to disk by default, so a repeated call for the same data
doesn't re-fetch it:

```python
import asyncio
import time

from ranobelib import RanobeLib


async def main() -> None:
    async with RanobeLib(
        "https://ranobelib.me/ru/book/91443--new-hero-in-dxd", cache_dir=".ranobelib_cache"
    ) as lib:
        start = time.perf_counter()
        await lib.get_table_of_contents()
        print(f"first call:  {time.perf_counter() - start:.3f}s (hits the API)")

        start = time.perf_counter()
        await lib.get_table_of_contents()
        print(f"second call: {time.perf_counter() - start:.3f}s (served from disk cache)")

        await lib.get_table_of_contents(refresh=True)  # Bypasses the cache explicitly.


asyncio.run(main())
```

**Result** (your exact timings will vary, but the gap between the two calls won't):

```
first call:  0.318s (hits the API)
second call: 0.001s (served from disk cache)
```

### Exporting to txt / fb2 / epub / pdf

```python
import asyncio

from ranobelib import RanobeLib


async def main() -> None:
    async with RanobeLib("https://ranobelib.me/ru/book/91443--new-hero-in-dxd") as lib:
        chapters = await lib.get_chapters([(1, "1"), (1, "2")])
        for fmt in ("txt", "fb2", "epub", "pdf"):
            path = f"output.{fmt}"
            result = await lib.export(chapters, fmt=fmt, path=path)
            print(fmt, "->", result)


asyncio.run(main())
```

**Result** (file sizes from the real run — `pdf` needs
[WeasyPrint's native dependencies](https://doc.courtbouillon.org/weasyprint/stable/first_steps.html#installation)
installed; without them this raises `ValueError: Unknown export format 'pdf'. Available:
epub, fb2, txt` instead of the line shown here):

```
txt -> output.txt      (84,044 bytes)
fb2 -> output.fb2      (87,691 bytes)
epub -> output.epub  (1,442,724 bytes, cover + illustrations embedded)
pdf -> output.pdf      (cover + illustrations embedded, needs WeasyPrint)
```

`output.txt`'s first few lines, for a sense of the format:

```
New Hero in DxD


Volume 1, Chapter 1: Глава 1

"Наконец, я наконец-то могу вернуться." - говорю я с широкой улыбкой на лице, хотя по моим
щекам текут слезы. Прошло слишком много времени с тех пор, как я застрял в этом месте, я
больше не могу с этим справляться. Поначалу это было круто, но через нек...
```

### Error handling

```python
import asyncio

from ranobelib import ChapterNotFoundError, RanobeLib, TitleNotFoundError


async def main() -> None:
    async with RanobeLib("https://ranobelib.me/ru/book/1--this-title-does-not-exist-zzz") as lib:
        try:
            await lib.get_info()
        except TitleNotFoundError as exc:
            print(exc)

    async with RanobeLib("https://ranobelib.me/ru/book/91443--new-hero-in-dxd") as lib:
        try:
            await lib.get_chapter(volume=999, number="9999")
        except ChapterNotFoundError as exc:
            print(exc)


asyncio.run(main())
```

**Result:**

```
Title not found: '1--this-title-does-not-exist-zzz'
Chapter not found: '91443--new-hero-in-dxd' volume='999' number='9999'
```

`AuthRequiredError` (403, paid/early-access content) and `RateLimitError` (429 after
retries are exhausted) follow the same pattern — see the
[API reference](https://LLIJIYAPNIK.github.io/ranobelib-python-sdk/reference/) for every
exception's attributes.

## Documentation

Full API reference and guides: **<https://LLIJIYAPNIK.github.io/ranobelib-python-sdk/>**
(built with `mkdocs-material` + `mkdocstrings`, deployed on push to `main`). `CLAUDE.md`
documents the full architecture, public API contract, and the reasoning behind the SDK's
design decisions.

## License

MIT — see [LICENSE](LICENSE).
