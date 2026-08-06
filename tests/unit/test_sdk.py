"""Unit tests for ranobelib.sdk helpers."""

from typing import Any

import pytest

from ranobelib.models import Chapter
from ranobelib.sdk import RanobeLib, _group_into_volumes, _resolve_bulk_branch_id


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


def _raw_branch(branch_id: int) -> dict[str, int]:
    return {"id": branch_id * 1000, "branch_id": branch_id}


def test_resolve_bulk_branch_id_matches_branch_id_regardless_of_position() -> None:
    branches = [_raw_branch(635), _raw_branch(2251)]

    resolved, selected = _resolve_bulk_branch_id(branches, branch_id=2251, translation_index=None)

    assert resolved is True
    assert selected == 2251


def test_resolve_bulk_branch_id_fails_when_branch_id_not_among_branches() -> None:
    branches = [_raw_branch(635), _raw_branch(2251)]

    resolved, selected = _resolve_bulk_branch_id(branches, branch_id=999, translation_index=None)

    assert resolved is False
    assert selected is None


def test_resolve_bulk_branch_id_uses_translation_index_position() -> None:
    branches = [_raw_branch(635), _raw_branch(2251)]

    resolved, selected = _resolve_bulk_branch_id(branches, branch_id=None, translation_index=1)

    assert resolved is True
    assert selected == 2251


def test_resolve_bulk_branch_id_fails_when_translation_index_out_of_range() -> None:
    branches = [_raw_branch(635), _raw_branch(2251)]

    resolved, selected = _resolve_bulk_branch_id(branches, branch_id=None, translation_index=5)

    assert resolved is False
    assert selected is None


def test_resolve_bulk_branch_id_fails_when_neither_option_given() -> None:
    branches = [_raw_branch(635), _raw_branch(2251)]

    resolved, selected = _resolve_bulk_branch_id(branches, branch_id=None, translation_index=None)

    assert resolved is False
    assert selected is None


def _raw_toc_chapter(
    volume: str, number: str, *, branches: list[dict[str, Any]] | None = None
) -> dict[str, Any]:
    return {"volume": volume, "number": number, "branches": branches or []}


def _fake_content_chapter(volume_str: str, number: str, branch_id: int | None) -> Chapter:
    return Chapter.model_validate(
        {"id": 1, "volume": volume_str, "number": number, "content": "<p>" + "x" * 40 + "</p>"}
    )


async def test_estimate_title_size_samples_evenly_and_extrapolates(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    raw_chapters = [_raw_toc_chapter("1", str(index)) for index in range(10)]
    fetched: list[str] = []

    async def fake_get_chapters(*, refresh: bool = False) -> list[dict[str, Any]]:
        return raw_chapters

    async def fake_fetch_chapter(
        volume_str: str, number: str, branch_id: int | None, *, refresh: bool = False
    ) -> Chapter:
        fetched.append(number)
        return _fake_content_chapter(volume_str, number, branch_id)

    async with RanobeLib("1--slug") as lib:
        monkeypatch.setattr(lib, "_get_chapters", fake_get_chapters)
        monkeypatch.setattr(lib, "_fetch_chapter", fake_fetch_chapter)

        estimate = await lib.estimate_title_size(sample_size=3)

    # Evenly spread across all 10 chapters, not just the first 3.
    assert fetched == ["0", "3", "6"]
    assert estimate > 0


async def test_estimate_title_size_clamps_sample_size_to_chapter_count(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    raw_chapters = [_raw_toc_chapter("1", str(index)) for index in range(2)]
    fetched: list[str] = []

    async def fake_get_chapters(*, refresh: bool = False) -> list[dict[str, Any]]:
        return raw_chapters

    async def fake_fetch_chapter(
        volume_str: str, number: str, branch_id: int | None, *, refresh: bool = False
    ) -> Chapter:
        fetched.append(number)
        return _fake_content_chapter(volume_str, number, branch_id)

    async with RanobeLib("1--slug") as lib:
        monkeypatch.setattr(lib, "_get_chapters", fake_get_chapters)
        monkeypatch.setattr(lib, "_fetch_chapter", fake_fetch_chapter)

        await lib.estimate_title_size(sample_size=5)

    assert fetched == ["0", "1"]


async def test_estimate_title_size_skips_unresolved_ambiguous_chapters(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    raw_chapters = [
        _raw_toc_chapter("1", "0", branches=[_raw_branch(1), _raw_branch(2)]),
        _raw_toc_chapter("1", "1"),
    ]
    fetched: list[str] = []

    async def fake_get_chapters(*, refresh: bool = False) -> list[dict[str, Any]]:
        return raw_chapters

    async def fake_fetch_chapter(
        volume_str: str, number: str, branch_id: int | None, *, refresh: bool = False
    ) -> Chapter:
        fetched.append(number)
        return _fake_content_chapter(volume_str, number, branch_id)

    async with RanobeLib("1--slug") as lib:
        monkeypatch.setattr(lib, "_get_chapters", fake_get_chapters)
        monkeypatch.setattr(lib, "_fetch_chapter", fake_fetch_chapter)

        estimate = await lib.estimate_title_size()

    # Chapter "0" is ambiguous with no branch_id/translation_index to resolve it — skipped as
    # a sampling candidate rather than raising, unlike download_title().
    assert fetched == ["1"]
    assert estimate > 0


async def test_estimate_title_size_resolves_ambiguous_chapter_via_branch_id(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    raw_chapters = [
        _raw_toc_chapter("1", "0", branches=[_raw_branch(635), _raw_branch(2251)]),
        _raw_toc_chapter("1", "1"),
    ]
    fetched: list[tuple[str, int | None]] = []

    async def fake_get_chapters(*, refresh: bool = False) -> list[dict[str, Any]]:
        return raw_chapters

    async def fake_fetch_chapter(
        volume_str: str, number: str, branch_id: int | None, *, refresh: bool = False
    ) -> Chapter:
        fetched.append((number, branch_id))
        return _fake_content_chapter(volume_str, number, branch_id)

    async with RanobeLib("1--slug") as lib:
        monkeypatch.setattr(lib, "_get_chapters", fake_get_chapters)
        monkeypatch.setattr(lib, "_fetch_chapter", fake_fetch_chapter)

        estimate = await lib.estimate_title_size(branch_id=2251)

    # Both chapters resolve now: "0" via the given branch_id, "1" has no ambiguity at all.
    assert fetched == [("0", 2251), ("1", None)]
    assert estimate > 0


async def test_estimate_title_size_returns_zero_when_no_chapter_resolves(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    raw_chapters = [_raw_toc_chapter("1", "0", branches=[_raw_branch(1), _raw_branch(2)])]

    async def fake_get_chapters(*, refresh: bool = False) -> list[dict[str, Any]]:
        return raw_chapters

    async with RanobeLib("1--slug") as lib:
        monkeypatch.setattr(lib, "_get_chapters", fake_get_chapters)

        estimate = await lib.estimate_title_size()

    assert estimate == 0


async def test_estimate_title_size_returns_zero_for_title_with_no_chapters(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    async def fake_get_chapters(*, refresh: bool = False) -> list[dict[str, Any]]:
        return []

    async with RanobeLib("1--slug") as lib:
        monkeypatch.setattr(lib, "_get_chapters", fake_get_chapters)

        estimate = await lib.estimate_title_size()

    assert estimate == 0


async def test_estimate_title_size_raises_value_error_when_both_selectors_given() -> None:
    async with RanobeLib("1--slug") as lib:
        with pytest.raises(ValueError, match="not both"):
            await lib.estimate_title_size(branch_id=1, translation_index=0)


async def test_estimate_title_size_raises_value_error_for_non_positive_sample_size() -> None:
    async with RanobeLib("1--slug") as lib:
        with pytest.raises(ValueError, match="sample_size"):
            await lib.estimate_title_size(sample_size=0)
