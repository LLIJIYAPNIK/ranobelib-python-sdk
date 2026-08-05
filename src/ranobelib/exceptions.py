"""Custom exceptions raised by the SDK."""

from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from ranobelib.models import ChapterBranch


class RanobeLibError(Exception):
    """Base class for all errors raised by the SDK."""


class TitleNotFoundError(RanobeLibError):
    """Raised when a title cannot be found on ranobelib.me.

    Attributes:
        slug_url: The title's ``{id}--{slug}`` identifier that couldn't be found.
    """

    def __init__(self, slug_url: str) -> None:
        self.slug_url = slug_url
        super().__init__(f"Title not found: {slug_url!r}")


class ChapterNotFoundError(RanobeLibError):
    """Raised when a chapter cannot be found for a given volume/number.

    Attributes:
        slug_url: The title's ``{id}--{slug}`` identifier.
        volume: The volume number that was requested.
        number: The chapter number that was requested.
    """

    def __init__(self, slug_url: str, *, volume: str, number: str) -> None:
        self.slug_url = slug_url
        self.volume = volume
        self.number = number
        super().__init__(f"Chapter not found: {slug_url!r} volume={volume!r} number={number!r}")


class VolumeNotFoundError(RanobeLibError):
    """Raised when a title has no chapters for a given volume number.

    Attributes:
        slug_url: The title's ``{id}--{slug}`` identifier.
        volume: The volume number that was requested.
    """

    def __init__(self, slug_url: str, *, volume: str) -> None:
        self.slug_url = slug_url
        self.volume = volume
        super().__init__(f"Volume not found: {slug_url!r} volume={volume!r}")


class MultipleTranslationsError(RanobeLibError):
    """Raised when a chapter has more than one team's translation and none was selected.

    The SDK does not guess a default: the API's own default when ``branch_id`` is omitted
    is not simply the first branch listed, and the actual rule it uses isn't documented
    (see docs/api-notes.md) — returning it silently would be unpredictable. Call
    ``RanobeLib.get_translations()`` to list the available branches, then pass one's
    ``branch_id`` explicitly.

    Attributes:
        slug_url: The title's ``{id}--{slug}`` identifier.
        volume: The chapter's volume number.
        number: The chapter number.
        branches: The chapter's available translations, as returned by
            ``RanobeLib.get_translations()``.
    """

    def __init__(
        self, slug_url: str, *, volume: str, number: str, branches: list[ChapterBranch]
    ) -> None:
        self.slug_url = slug_url
        self.volume = volume
        self.number = number
        self.branches = branches
        options = ", ".join(
            f"branch_id={branch.branch_id} ({_describe_branch(branch)})" for branch in branches
        )
        super().__init__(
            f"Multiple translations for {slug_url!r} volume={volume!r} number={number!r}: "
            f"{options}. Pass branch_id to select one (see RanobeLib.get_translations())."
        )


def _describe_branch(branch: ChapterBranch) -> str:
    if branch.teams:
        return ", ".join(team.name for team in branch.teams)
    return branch.user.username


class AuthRequiredError(RanobeLibError):
    """Raised when the requested content requires authorization (paid or early access).

    Attributes:
        url: The request URL that returned 403.
    """

    def __init__(self, url: str) -> None:
        self.url = url
        super().__init__(f"Authorization required to access: {url}")


class RateLimitError(RanobeLibError):
    """Raised when the API responds with 429 Too Many Requests.

    Attributes:
        retry_after: The response's ``Retry-After`` value, in seconds, if it sent one.
    """

    def __init__(self, retry_after: float | None = None) -> None:
        self.retry_after = retry_after
        suffix = f" (retry after {retry_after}s)" if retry_after is not None else ""
        super().__init__(f"Rate limited by the API{suffix}")
