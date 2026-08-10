"""Integration tests for Catalog.list_titles(), backed by VCR cassettes.

These exercise the real api.cdnlibs.org API. Cassettes are recorded once (see
tests/conftest.py, record_mode="once") and replayed afterwards, so CI does not need
network access.
"""

from pathlib import Path

import pytest

from ranobelib import Catalog, CatalogPage, Genre, Title


@pytest.mark.vcr
async def test_list_titles_returns_matching_titles() -> None:
    async with Catalog() as catalog:
        page = await catalog.list_titles(query="dxd")

    assert isinstance(page, CatalogPage)
    assert page.page == 1
    assert isinstance(page.has_next_page, bool)
    assert page.items
    assert all(isinstance(item, Title) for item in page.items)
    # Every result should be a real DxD-adjacent title, matched by name/rus_name/eng_name.
    assert any("dxd" in (item.eng_name or "").lower() for item in page.items)


@pytest.mark.vcr
async def test_list_titles_filters_by_status() -> None:
    async with Catalog() as catalog:
        page = await catalog.list_titles(status=1, per_page=10)

    assert page.items
    assert all(item.status.id == 1 for item in page.items)


@pytest.mark.vcr
async def test_list_titles_filters_by_genres_and_status_combined() -> None:
    async with Catalog() as catalog:
        page = await catalog.list_titles(genres=[34], status=1, per_page=10)

    assert isinstance(page, CatalogPage)
    assert all(item.status.id == 1 for item in page.items)


@pytest.mark.vcr
async def test_list_titles_pagination_advances_to_different_items() -> None:
    async with Catalog() as catalog:
        first = await catalog.list_titles(page=1, per_page=10, sort="name")
        second = await catalog.list_titles(page=2, per_page=10, sort="name")

    first_ids = {item.id for item in first.items}
    second_ids = {item.id for item in second.items}
    assert first_ids.isdisjoint(second_ids)


@pytest.mark.vcr
async def test_list_titles_page_past_the_end_returns_empty_with_no_more_pages() -> None:
    async with Catalog() as catalog:
        page = await catalog.list_titles(page=99999, status=1, per_page=10)

    assert page.items == []
    assert page.has_next_page is False


@pytest.mark.vcr
async def test_list_titles_second_call_same_params_is_served_from_cache(
    tmp_path: Path, vcr: object
) -> None:
    async with Catalog(cache_dir=tmp_path) as catalog:
        first = await catalog.list_titles(query="dxd")
        second = await catalog.list_titles(query="dxd")

    assert first == second
    assert len(vcr.requests) == 1  # type: ignore[attr-defined]


@pytest.mark.vcr
async def test_list_titles_refresh_bypasses_cache(tmp_path: Path, vcr: object) -> None:
    async with Catalog(cache_dir=tmp_path) as catalog:
        await catalog.list_titles(query="dxd")
        await catalog.list_titles(query="dxd", refresh=True)

    assert len(vcr.requests) == 2  # type: ignore[attr-defined]


async def test_list_titles_rejects_page_below_one() -> None:
    async with Catalog() as catalog:
        with pytest.raises(ValueError, match="page"):
            await catalog.list_titles(page=0)


@pytest.mark.parametrize("per_page", [9, 61])
async def test_list_titles_rejects_per_page_out_of_range(per_page: int) -> None:
    async with Catalog() as catalog:
        with pytest.raises(ValueError, match="per_page"):
            await catalog.list_titles(per_page=per_page)


@pytest.mark.vcr
async def test_list_genres_returns_genres_with_id_and_name() -> None:
    async with Catalog() as catalog:
        genres = await catalog.list_genres()

    assert genres
    assert all(isinstance(genre, Genre) for genre in genres)
    assert all(genre.id and genre.name for genre in genres)
    # Genre 34 is used elsewhere in this test suite as a `list_titles(genres=[34])` filter
    # value (see test_list_titles_filters_by_genres_and_status_combined) — confirm it
    # resolves to a real name here.
    assert any(genre.id == 34 and genre.name == "Боевик" for genre in genres)


@pytest.mark.vcr
async def test_list_genres_excludes_genres_not_tagged_for_ranobelib() -> None:
    async with Catalog() as catalog:
        genres = await catalog.list_genres()

    # Genre 88 ("Детское") is tagged site_ids: [5] only in the raw API response (see
    # docs/api-notes.md) — ranobelib.me is site 3, so it must be filtered out.
    assert all(genre.id != 88 for genre in genres)


@pytest.mark.vcr
async def test_list_genres_second_call_same_params_is_served_from_cache(
    tmp_path: Path, vcr: object
) -> None:
    async with Catalog(cache_dir=tmp_path) as catalog:
        first = await catalog.list_genres()
        second = await catalog.list_genres()

    assert first == second
    assert len(vcr.requests) == 1  # type: ignore[attr-defined]


@pytest.mark.vcr
async def test_list_genres_refresh_bypasses_cache(tmp_path: Path, vcr: object) -> None:
    async with Catalog(cache_dir=tmp_path) as catalog:
        await catalog.list_genres()
        await catalog.list_genres(refresh=True)

    assert len(vcr.requests) == 2  # type: ignore[attr-defined]
