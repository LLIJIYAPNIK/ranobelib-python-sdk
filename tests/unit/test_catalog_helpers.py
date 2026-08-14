"""Unit tests for ranobelib.catalog helpers (no network)."""

from ranobelib.catalog import _build_countries, _build_genres, _build_page, _cache_key
from ranobelib.models import CatalogPage, Country, Genre, Title

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
    key1 = _cache_key(
        page=1,
        per_page=30,
        query=None,
        genres=None,
        tags=None,
        status=None,
        countries=None,
        sort="name",
    )
    key2 = _cache_key(
        page=2,
        per_page=30,
        query=None,
        genres=None,
        tags=None,
        status=None,
        countries=None,
        sort="name",
    )

    assert key1 != key2


def test_cache_key_differs_by_query_genres_tags_status_countries_and_sort() -> None:
    base = _cache_key(
        page=1,
        per_page=30,
        query=None,
        genres=None,
        tags=None,
        status=None,
        countries=None,
        sort="name",
    )

    assert base != _cache_key(
        page=1,
        per_page=30,
        query="dxd",
        genres=None,
        tags=None,
        status=None,
        countries=None,
        sort="name",
    )
    assert base != _cache_key(
        page=1,
        per_page=30,
        query=None,
        genres=[34],
        tags=None,
        status=None,
        countries=None,
        sort="name",
    )
    assert base != _cache_key(
        page=1,
        per_page=30,
        query=None,
        genres=None,
        tags=[218],
        status=None,
        countries=None,
        sort="name",
    )
    assert base != _cache_key(
        page=1,
        per_page=30,
        query=None,
        genres=None,
        tags=None,
        status=1,
        countries=None,
        sort="name",
    )
    assert base != _cache_key(
        page=1,
        per_page=30,
        query=None,
        genres=None,
        tags=None,
        status=None,
        countries=[10],
        sort="name",
    )
    assert base != _cache_key(
        page=1,
        per_page=30,
        query=None,
        genres=None,
        tags=None,
        status=None,
        countries=None,
        sort="views",
    )


def test_cache_key_stable_for_equivalent_calls() -> None:
    key1 = _cache_key(
        page=1,
        per_page=30,
        query="dxd",
        genres=[1, 2],
        tags=[218],
        status=1,
        countries=[10, 11],
        sort="name",
    )
    key2 = _cache_key(
        page=1,
        per_page=30,
        query="dxd",
        genres=[1, 2],
        tags=[218],
        status=1,
        countries=[10, 11],
        sort="name",
    )

    assert key1 == key2


def test_build_genres_validates_items_as_genre() -> None:
    data = [{"id": 34, "name": "Боевик", "adult": False, "site_ids": [1, 2, 3, 4, 5]}]

    genres = _build_genres(data)

    assert genres == [Genre(id=34, name="Боевик", adult=False)]


def test_build_genres_drops_genres_not_tagged_for_ranobelib() -> None:
    data = [
        {"id": 34, "name": "Боевик", "adult": False, "site_ids": [1, 2, 3, 4, 5]},
        {"id": 88, "name": "Детское", "adult": False, "site_ids": [5]},
    ]

    genres = _build_genres(data)

    assert [genre.id for genre in genres] == [34]


def test_build_genres_handles_empty_results() -> None:
    assert _build_genres([]) == []


def test_build_countries_validates_items_as_country() -> None:
    data = [{"id": 10, "label": "Япония", "site_ids": [3]}]

    countries = _build_countries(data)

    assert countries == [Country(id=10, name="Япония")]


def test_build_countries_drops_countries_not_tagged_for_ranobelib() -> None:
    data = [
        {"id": 10, "label": "Япония", "site_ids": [3]},
        {"id": 1, "label": "Манга", "site_ids": [1, 2, 4]},
    ]

    countries = _build_countries(data)

    assert [country.id for country in countries] == [10]


def test_build_countries_handles_empty_results() -> None:
    assert _build_countries([]) == []
