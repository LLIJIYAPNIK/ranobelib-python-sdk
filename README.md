# ranobelib-python-sdk

Async Python SDK for [ranobelib.me](https://ranobelib.me): fetch title metadata, download
chapters and volumes, and export to epub, fb2, txt, or pdf.

The SDK talks to the undocumented but open JSON API behind the site (`api.cdnlibs.org`,
part of the lib.social network) instead of scraping HTML.

> **Status:** early development. All the calls in the quickstart below are implemented:
> `RanobeLib.get_info()`, `get_table_of_contents()`, `get_chapter()`, `get_volume()`,
> `get_chapters()`, `get_volumes()`, `get_translations()` (with `branch_id`-based
> translation selection), and `export(chapters, fmt=..., path=...)` to `"txt"`, `"fb2"`,
> `"epub"`, or `"pdf"` (cover + in-chapter illustrations embedded in epub/pdf). Raw API
> responses are cached to disk (`cache_dir`/`cache_ttl` on the constructor, `refresh=True`
> on individual fetches) and the underlying client bounds concurrency, paces requests, and
> retries 429/5xx with backoff. `fmt="pdf"` needs WeasyPrint's native dependencies (Pango/
> cairo/GTK3) installed on the system — `pip install`/`uv add` alone doesn't guarantee that
> on every platform; without them, `export(fmt="pdf")` raises the same "unknown format"
> error the other three formats don't. See `CLAUDE.md` for what's still ahead
> (documentation).

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

    await lib.export(chapters, fmt="epub", path="output.epub")
```

This is the full current public API — everything above is implemented and works today.

## Documentation

Full API reference and guides will be published via GitHub Pages once `mkdocs` is set up
(see the documentation step in the project roadmap). Until then, `CLAUDE.md` documents the
architecture and public API contract.

## License

MIT — see [LICENSE](LICENSE).
