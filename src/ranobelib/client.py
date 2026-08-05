"""Low-level HTTP client for the api.cdnlibs.org JSON API."""

from __future__ import annotations

import asyncio
import time
from collections.abc import Awaitable, Callable
from types import TracebackType
from typing import Any, Self

import httpx

from ranobelib.exceptions import (
    AuthRequiredError,
    ChapterNotFoundError,
    RanobeLibError,
    RateLimitError,
    TitleNotFoundError,
)

API_BASE_URL = "https://api.cdnlibs.org/api"
"""Base URL of the lib.social JSON API shared across the network's sites."""

RANOBELIB_SITE_ID = "3"
"""``Site-Id`` header value that scopes requests to ranobelib.me. See docs/api-notes.md."""

_RETRYABLE_STATUSES = frozenset({429, *range(500, 600)})

DEFAULT_REQUEST_DELAY = 0.2
"""Default minimum time, in seconds, between the start of one request and the next."""


class ApiClient:
    """Thin async wrapper around the undocumented api.cdnlibs.org JSON API.

    Bounds concurrency with a semaphore, paces request starts with a small fixed delay, and
    retries 429/5xx responses with exponential backoff — see docs/api-notes.md for why a
    manual implementation was chosen over a dependency like ``tenacity`` for this.
    """

    def __init__(
        self,
        *,
        base_url: str = API_BASE_URL,
        timeout: float = 15.0,
        transport: httpx.AsyncBaseTransport | None = None,
        max_concurrency: int = 5,
        request_delay: float | None = None,
        max_retries: int = 3,
        retry_base_delay: float = 1.0,
        sleep: Callable[[float], Awaitable[None]] = asyncio.sleep,
        clock: Callable[[], float] = time.monotonic,
    ) -> None:
        """Initialize the client.

        Args:
            base_url: API base URL.
            timeout: Per-request timeout, in seconds.
            transport: Custom ``httpx`` transport, e.g. a mock transport for tests.
            max_concurrency: Maximum number of requests in flight at once.
            request_delay: Minimum time, in seconds, between the start of one request and
                the next, even under ``max_concurrency``. ``None`` (the default) uses
                ``DEFAULT_REQUEST_DELAY``.
            max_retries: How many times to retry a 429 or 5xx response before giving up and
                raising.
            retry_base_delay: Base delay, in seconds, for exponential backoff between
                retries (doubled per attempt) — used unless a 429 response's
                ``Retry-After`` header says otherwise.
            sleep: Sleep function used for pacing and backoff. Overridable for tests.
            clock: Time source used for pacing. Overridable for tests.
        """
        self._http = httpx.AsyncClient(
            base_url=base_url,
            timeout=timeout,
            transport=transport,
            headers={
                "Site-Id": RANOBELIB_SITE_ID,
                "Accept": "application/json",
            },
        )
        self._semaphore = asyncio.Semaphore(max_concurrency)
        self._request_delay = DEFAULT_REQUEST_DELAY if request_delay is None else request_delay
        self._max_retries = max_retries
        self._retry_base_delay = retry_base_delay
        self._sleep = sleep
        self._clock = clock
        self._pacing_lock = asyncio.Lock()
        self._last_request_at: float | None = None

    async def __aenter__(self) -> Self:
        return self

    async def __aexit__(
        self,
        exc_type: type[BaseException] | None,
        exc: BaseException | None,
        traceback: TracebackType | None,
    ) -> None:
        await self.aclose()

    async def aclose(self) -> None:
        """Close the underlying HTTP connection pool."""
        await self._http.aclose()

    async def get_title(self, slug_url: str, *, fields: list[str] | None = None) -> dict[str, Any]:
        """Fetch raw title metadata for ``slug_url``.

        Args:
            slug_url: The title's ``{id}--{slug}`` identifier.
            fields: Extra ``fields[]`` values to request from the API.

        Returns:
            The ``data`` object from the API response.
        """
        params = httpx.QueryParams([("fields[]", field) for field in fields or []])
        response = await self._get(f"/manga/{slug_url}", params=params)
        self._raise_for_status(response, not_found=TitleNotFoundError(slug_url))
        data: dict[str, Any] = response.json()["data"]
        return data

    async def get_chapters(self, slug_url: str) -> list[dict[str, Any]]:
        """Fetch the raw chapter list for ``slug_url`` (single request, no pagination).

        Args:
            slug_url: The title's ``{id}--{slug}`` identifier.

        Returns:
            The ``data`` array from the API response.
        """
        response = await self._get(f"/manga/{slug_url}/chapters")
        self._raise_for_status(response, not_found=TitleNotFoundError(slug_url))
        data: list[dict[str, Any]] = response.json()["data"]
        return data

    async def get_chapter(
        self,
        slug_url: str,
        *,
        number: str,
        volume: str,
        branch_id: int | None = None,
    ) -> dict[str, Any]:
        """Fetch a single chapter's metadata and content.

        Args:
            slug_url: The title's ``{id}--{slug}`` identifier.
            number: The chapter number, as returned by the API (may contain a decimal).
            volume: The volume number.
            branch_id: Which translation team's branch to fetch, for chapters with more
                than one. Defaults to whichever branch the API picks (see
                docs/api-notes.md — this is not simply the first branch listed).

        Returns:
            The ``data`` object from the API response.
        """
        params = {"number": number, "volume": volume}
        if branch_id is not None:
            params["branch_id"] = str(branch_id)
        response = await self._get(f"/manga/{slug_url}/chapter", params=params)
        self._raise_for_status(
            response, not_found=ChapterNotFoundError(slug_url, volume=volume, number=number)
        )
        data: dict[str, Any] = response.json()["data"]
        return data

    async def _get(self, url: str, *, params: Any = None) -> httpx.Response:
        """Issue a GET request, bounded by concurrency/pacing and retried on 429/5xx."""
        attempt = 0
        while True:
            async with self._semaphore:
                await self._pace()
                response = await self._http.get(url, params=params)
            if response.status_code not in _RETRYABLE_STATUSES or attempt >= self._max_retries:
                return response
            await self._sleep(self._backoff_delay(attempt, response))
            attempt += 1

    async def _pace(self) -> None:
        """Wait, if needed, so this request starts at least ``request_delay`` after the last."""
        async with self._pacing_lock:
            now = self._clock()
            if self._last_request_at is not None:
                wait = self._last_request_at + self._request_delay - now
                if wait > 0:
                    await self._sleep(wait)
            self._last_request_at = self._clock()

    def _backoff_delay(self, attempt: int, response: httpx.Response) -> float:
        if response.status_code == 429:
            retry_after = response.headers.get("Retry-After")
            if retry_after is not None:
                try:
                    return float(retry_after)
                except ValueError:
                    pass
        delay: float = self._retry_base_delay * (2**attempt)
        return delay

    def _raise_for_status(self, response: httpx.Response, *, not_found: RanobeLibError) -> None:
        if response.status_code == 404:
            raise not_found
        if response.status_code == 403:
            raise AuthRequiredError(str(response.request.url))
        if response.status_code == 429:
            retry_after = response.headers.get("Retry-After")
            raise RateLimitError(float(retry_after) if retry_after else None)
        try:
            response.raise_for_status()
        except httpx.HTTPStatusError as exc:
            raise RanobeLibError(f"Unexpected API response: {exc}") from exc
