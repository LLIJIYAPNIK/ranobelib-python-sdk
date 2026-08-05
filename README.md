# ranobelib-python-sdk

Async Python SDK for [ranobelib.me](https://ranobelib.me): fetch title metadata, download
chapters and volumes, and export to epub, fb2, txt, or pdf.

The SDK talks to the undocumented but open JSON API behind the site (`api.cdnlibs.org`,
part of the lib.social network) instead of scraping HTML.

> **Status:** early development. `RanobeLib.get_info()` is implemented; everything else in
> the quickstart below is the intended public API and not built yet — see `CLAUDE.md` for
> the planned roadmap.

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

    chapter = await lib.get_chapter(volume=6, number=51, number_secondary="6")
    volume = await lib.get_volume(volume=6)

    chapters = await lib.get_chapters([(6, "51", "6"), (6, "52", None)])
    volumes = await lib.get_volumes([1, 2, 3])

    translations = await lib.get_translations(volume=6, number=51, number_secondary="6")
    chapter = await lib.get_chapter(volume=6, number=51, number_secondary="6", team_id=...)

    await lib.export(chapters, fmt="epub", path="output.epub")
```

Only `get_info()` works today; the rest of this example describes the intended public API.

## Documentation

Full API reference and guides will be published via GitHub Pages once `mkdocs` is set up
(see the documentation step in the project roadmap). Until then, `CLAUDE.md` documents the
architecture and public API contract.

## License

MIT — see [LICENSE](LICENSE).
