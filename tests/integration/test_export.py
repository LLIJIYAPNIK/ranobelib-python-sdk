"""Integration tests for RanobeLib.export(), backed by VCR cassettes.

Exercises the full pipeline through the public facade: fetching chapters, then exporting
them with a registered exporter (currently "txt" and "fb2" — see exporters/txt.py and
exporters/fb2.py).
"""

from pathlib import Path

import pytest
from lxml import etree

from ranobelib import RanobeLib
from ranobelib.exporters.fb2 import FB2_NS


@pytest.mark.vcr
async def test_export_writes_txt_file_with_fetched_chapters(tmp_path: Path) -> None:
    output_path = tmp_path / "output.txt"
    async with RanobeLib("https://ranobelib.me/ru/book/91443--new-hero-in-dxd") as lib:
        chapters = await lib.get_chapters([(1, "1"), (1, "2")])
        result = await lib.export(chapters, fmt="txt", path=output_path)

    assert result == output_path
    text = output_path.read_text(encoding="utf-8")
    assert "Volume 1, Chapter 1" in text
    assert "Volume 1, Chapter 2" in text


@pytest.mark.vcr
async def test_export_writes_fb2_file_with_fetched_chapters(tmp_path: Path) -> None:
    output_path = tmp_path / "output.fb2"
    async with RanobeLib("https://ranobelib.me/ru/book/91443--new-hero-in-dxd") as lib:
        chapters = await lib.get_chapters([(1, "1"), (1, "2")])
        result = await lib.export(chapters, fmt="fb2", path=output_path)

    assert result == output_path
    root = etree.parse(str(output_path)).getroot()
    sections = root.findall(f"{{{FB2_NS}}}body/{{{FB2_NS}}}section")
    assert len(sections) == 2


async def test_export_raises_value_error_for_unknown_format(tmp_path: Path) -> None:
    # No @pytest.mark.vcr / cassette needed: an unknown fmt is rejected before any request.
    async with RanobeLib("https://ranobelib.me/ru/book/91443--new-hero-in-dxd") as lib:
        with pytest.raises(ValueError, match="Unknown export format"):
            await lib.export([], fmt="pdf", path=tmp_path / "output.pdf")
