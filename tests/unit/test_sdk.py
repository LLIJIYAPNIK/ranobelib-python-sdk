"""Unit tests for ranobelib.sdk helpers."""

from ranobelib.models import Chapter
from ranobelib.sdk import _group_into_volumes


def _chapter(*, volume: str, number: str, index: int) -> Chapter:
    return Chapter.model_validate(
        {
            "id": index,
            "volume": volume,
            "number": number,
            "name": f"Chapter {number}",
            "index": index,
            "item_number": index,
            "branches_count": 0,
            "branches": [],
            "bundle_id": None,
        }
    )


def test_group_into_volumes_preserves_api_order() -> None:
    chapters = [
        _chapter(volume="1", number="1", index=1),
        _chapter(volume="1", number="2", index=2),
        _chapter(volume="2", number="3", index=3),
    ]

    volumes = _group_into_volumes(chapters)

    assert [v.number for v in volumes] == ["1", "2"]
    assert [c.number for c in volumes[0].chapters] == ["1", "2"]
    assert [c.number for c in volumes[1].chapters] == ["3"]


def test_group_into_volumes_handles_empty_list() -> None:
    assert _group_into_volumes([]) == []


def test_group_into_volumes_keeps_first_seen_volume_order_even_if_interleaved() -> None:
    chapters = [
        _chapter(volume="0", number="0.1", index=1),
        _chapter(volume="1", number="1", index=2),
        _chapter(volume="0", number="0.2", index=3),
    ]

    volumes = _group_into_volumes(chapters)

    assert [v.number for v in volumes] == ["0", "1"]
    assert [c.number for c in volumes[0].chapters] == ["0.1", "0.2"]
