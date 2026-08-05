"""Unit tests for ranobelib.exceptions."""

from ranobelib.exceptions import (
    AuthRequiredError,
    ChapterNotFoundError,
    MultipleTranslationsError,
    RanobeLibError,
    RateLimitError,
    TitleNotFoundError,
    VolumeNotFoundError,
)
from ranobelib.models import ChapterBranch, ChapterUser, Team


def test_title_not_found_error_carries_slug_url() -> None:
    error = TitleNotFoundError("6712--high-school-dxd-novel")

    assert isinstance(error, RanobeLibError)
    assert error.slug_url == "6712--high-school-dxd-novel"
    assert "6712--high-school-dxd-novel" in str(error)


def test_chapter_not_found_error_carries_lookup_details() -> None:
    error = ChapterNotFoundError("6712--example", volume="5", number="51.6")

    assert isinstance(error, RanobeLibError)
    assert error.slug_url == "6712--example"
    assert error.volume == "5"
    assert error.number == "51.6"
    assert "6712--example" in str(error)
    assert "51.6" in str(error)


def test_volume_not_found_error_carries_lookup_details() -> None:
    error = VolumeNotFoundError("6712--example", volume="999")

    assert isinstance(error, RanobeLibError)
    assert error.slug_url == "6712--example"
    assert error.volume == "999"
    assert "6712--example" in str(error)
    assert "999" in str(error)


def test_auth_required_error_carries_url() -> None:
    url = "https://api.cdnlibs.org/api/manga/6712--example/chapter"
    error = AuthRequiredError(url)

    assert isinstance(error, RanobeLibError)
    assert error.url == url
    assert url in str(error)


def test_rate_limit_error_without_retry_after() -> None:
    error = RateLimitError()

    assert isinstance(error, RanobeLibError)
    assert error.retry_after is None
    assert "retry after" not in str(error)


def test_rate_limit_error_with_retry_after() -> None:
    error = RateLimitError(retry_after=12.5)

    assert error.retry_after == 12.5
    assert "12.5" in str(error)


def _branch(*, branch_id: int, teams: list[Team], username: str) -> ChapterBranch:
    return ChapterBranch(
        id=branch_id,
        branch_id=branch_id,
        created_at="2020-01-01T00:00:00.000000Z",
        teams=teams,
        user=ChapterUser(id=1, username=username),
    )


def test_multiple_translations_error_carries_lookup_details_and_branches() -> None:
    team = Team(id=13375, slug="berkud13", slug_url="13375--berkud13", name="BerkuD13")
    branches = [
        _branch(branch_id=2251, teams=[team], username="Birdzz"),
        _branch(branch_id=635, teams=[], username="ItsEND"),
    ]

    error = MultipleTranslationsError(
        "11407--solo-leveling", volume="1", number="0", branches=branches
    )

    assert isinstance(error, RanobeLibError)
    assert error.slug_url == "11407--solo-leveling"
    assert error.volume == "1"
    assert error.number == "0"
    assert error.branches == branches
    assert "11407--solo-leveling" in str(error)
    assert "branch_id=2251 (BerkuD13)" in str(error)
    assert "branch_id=635 (ItsEND)" in str(error)
