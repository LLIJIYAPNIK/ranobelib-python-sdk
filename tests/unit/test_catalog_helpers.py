"""Unit tests for ranobelib.catalog helpers (no network)."""

from ranobelib.catalog import _build_page, _cache_key
from ranobelib.models import CatalogPage, Title

_TITLE_ITEM = {
    "id": 1,
    "name": "Example",
    "slug": "example",
    "slug_url": "1--example",
    "cover": {},
    "ageRestriction": {"id": 0, "label": "16+"},
    "status": {"id": 1, "label": "Ongoing"},
}


def test_build_page_validates_items_as_title_and_reads_meta() -> None:
    data = {"data": [_TITLE_ITEM], "meta": {"current_page": 2, "has_next_page": True}}

    page = _build_page(data)

    assert isinstance(page, CatalogPage)
    assert len(page.items) == 1
    assert isinstance(page.items[0], Title)
    assert page.items[0].id == 1
    assert page.page == 2
    assert page.has_next_page is True


def test_build_page_handles_empty_results() -> None:
    data = {"data": [], "meta": {"current_page": 5, "has_next_page": False}}

    page = _build_page(data)

    assert page.items == []
    assert page.page == 5
    assert page.has_next_page is False


def test_cache_key_differs_by_page() -> None:
    key1 = _cache_key(page=1, per_page=30, query=None, genres=None, status=None, sort="name")
    key2 = _cache_key(page=2, per_page=30, query=None, genres=None, status=None, sort="name")

    assert key1 != key2


def test_cache_key_differs_by_query_genres_status_and_sort() -> None:
    base = _cache_key(page=1, per_page=30, query=None, genres=None, status=None, sort="name")

    assert base != _cache_key(
        page=1, per_page=30, query="dxd", genres=None, status=None, sort="name"
    )
    assert base != _cache_key(
        page=1, per_page=30, query=None, genres=[34], status=None, sort="name"
    )
    assert base != _cache_key(page=1, per_page=30, query=None, genres=None, status=1, sort="name")
    assert base != _cache_key(
        page=1, per_page=30, query=None, genres=None, status=None, sort="views"
    )


def test_cache_key_stable_for_equivalent_calls() -> None:
    key1 = _cache_key(page=1, per_page=30, query="dxd", genres=[1, 2], status=1, sort="name")
    key2 = _cache_key(page=1, per_page=30, query="dxd", genres=[1, 2], status=1, sort="name")

    assert key1 == key2
