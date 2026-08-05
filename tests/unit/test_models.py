"""Unit tests for ranobelib.models."""

from typing import Any

from ranobelib.models import Title

RAW_TITLE: dict[str, Any] = {
    "id": 91443,
    "name": "New Hero in DxD",
    "rus_name": "Новый герой в мире DXD (Новелла)",
    "eng_name": "New Hero in DxD (Novel)",
    "otherNames": [],
    "model": "manga",
    "slug": "new-hero-in-dxd",
    "slug_url": "91443--new-hero-in-dxd",
    "cover": {
        "filename": "CuhkYTqxqJc0",
        "thumbnail": "https://cover.cdnlibs.org/.../thumb.jpg",
        "default": "https://cover.cdnlibs.org/.../250x350.jpg",
        "md": "https://cover.cdnlibs.org/.../250x350.jpg",
    },
    "ageRestriction": {"id": 1, "label": "6+"},
    "site": 3,
    "type": {"id": 15, "label": "Фанфик"},
    "summary": {
        "type": "doc",
        "content": [
            {
                "type": "paragraph",
                "content": [{"type": "text", "text": "Первый абзац."}],
            },
            {
                "type": "paragraph",
                "content": [
                    {"type": "text", "text": "Второй "},
                    {"type": "text", "text": "абзац."},
                ],
            },
        ],
    },
    "releaseDate": "2021",
    "is_licensed": False,
    "teams": [
        {
            "id": 23286,
            "slug": "stixs-team",
            "slug_url": "23286--stixs-team",
            "model": "team",
            "name": "Stixs TEAM",
        }
    ],
    "genres": [{"id": 37, "name": "Гарем", "adult": False, "alert": False}],
    "tags": [{"id": 218, "name": "Богиня", "adult": False, "alert": False}],
    "authors": [
        {
            "id": 57847,
            "slug": "kingch",
            "slug_url": "57847--kingch",
            "model": "people",
            "name": "kingCH",
            "rus_name": None,
        }
    ],
    "content_marking": [],
    "status": {"id": 1, "label": "Онгоинг"},
    "items_count": {"uploaded": 47, "total": 0},
    "scanlateStatus": {"id": 4, "label": "Забросили"},
    "artists": [],
    "releaseDateString": "2021 г.",
}


def test_title_model_validate_maps_aliases_and_nested_models() -> None:
    title = Title.model_validate(RAW_TITLE)

    assert title.id == 91443
    assert title.name == "New Hero in DxD"
    assert title.rus_name == "Новый герой в мире DXD (Новелла)"
    assert title.other_names == []
    assert title.slug_url == "91443--new-hero-in-dxd"
    assert title.cover.filename == "CuhkYTqxqJc0"
    assert title.age_restriction.label == "6+"
    assert title.status.label == "Онгоинг"
    assert title.release_date == "2021"
    assert title.teams[0].name == "Stixs TEAM"
    assert title.genres[0].name == "Гарем"
    assert title.tags[0].name == "Богиня"
    assert title.authors[0].name == "kingCH"
    assert title.artists == []


def test_title_model_parses_prosemirror_summary_to_text() -> None:
    title = Title.model_validate(RAW_TITLE)

    assert title.summary == "Первый абзац.\n\nВторой абзац."


def test_title_model_flattens_chapter_count_from_items_count() -> None:
    title = Title.model_validate(RAW_TITLE)

    assert title.chapter_count == 47


def test_title_model_chapter_count_is_none_without_items_count() -> None:
    raw = {k: v for k, v in RAW_TITLE.items() if k != "items_count"}

    title = Title.model_validate(raw)

    assert title.chapter_count is None


def test_title_model_summary_none_stays_none() -> None:
    raw = {**RAW_TITLE, "summary": None}

    title = Title.model_validate(raw)

    assert title.summary is None


def test_title_model_summary_accepts_plain_string() -> None:
    raw = {**RAW_TITLE, "summary": "Already plain text."}

    title = Title.model_validate(raw)

    assert title.summary == "Already plain text."


def test_title_model_handles_missing_optional_fields() -> None:
    minimal = {
        "id": 1,
        "name": "Minimal Title",
        "slug": "minimal-title",
        "slug_url": "1--minimal-title",
        "cover": {},
        "ageRestriction": {"id": 1, "label": "6+"},
        "status": {"id": 1, "label": "Онгоинг"},
    }

    title = Title.model_validate(minimal)

    assert title.summary is None
    assert title.chapter_count is None
    assert title.other_names == []
    assert title.genres == []
