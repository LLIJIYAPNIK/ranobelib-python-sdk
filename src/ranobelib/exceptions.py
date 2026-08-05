"""Custom exceptions raised by the SDK."""

from __future__ import annotations


class RanobeLibError(Exception):
    """Base class for all errors raised by the SDK."""


class TitleNotFoundError(RanobeLibError):
    """Raised when a title cannot be found on ranobelib.me."""

    def __init__(self, slug_url: str) -> None:
        self.slug_url = slug_url
        super().__init__(f"Title not found: {slug_url!r}")


class ChapterNotFoundError(RanobeLibError):
    """Raised when a chapter cannot be found for a given volume/number."""

    def __init__(self, slug_url: str, *, volume: str, number: str) -> None:
        self.slug_url = slug_url
        self.volume = volume
        self.number = number
        super().__init__(f"Chapter not found: {slug_url!r} volume={volume!r} number={number!r}")


class AuthRequiredError(RanobeLibError):
    """Raised when the requested content requires authorization (paid or early access)."""

    def __init__(self, url: str) -> None:
        self.url = url
        super().__init__(f"Authorization required to access: {url}")


class RateLimitError(RanobeLibError):
    """Raised when the API responds with 429 Too Many Requests."""

    def __init__(self, retry_after: float | None = None) -> None:
        self.retry_after = retry_after
        suffix = f" (retry after {retry_after}s)" if retry_after is not None else ""
        super().__init__(f"Rate limited by the API{suffix}")
