"""Unit tests for ranobelib.exceptions."""

from ranobelib.exceptions import (
    AuthRequiredError,
    RanobeLibError,
    RateLimitError,
    TitleNotFoundError,
)


def test_title_not_found_error_carries_slug_url() -> None:
    error = TitleNotFoundError("6712--high-school-dxd-novel")

    assert isinstance(error, RanobeLibError)
    assert error.slug_url == "6712--high-school-dxd-novel"
    assert "6712--high-school-dxd-novel" in str(error)


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
