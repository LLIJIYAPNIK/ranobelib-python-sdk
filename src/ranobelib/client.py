"""Low-level HTTP client for the api.cdnlibs.org JSON API."""

from __future__ import annotations

from types import TracebackType
from typing import Any, Self

import httpx

from ranobelib.exceptions import (
    AuthRequiredError,
    RanobeLibError,
    RateLimitError,
    TitleNotFoundError,
)

API_BASE_URL = "https://api.cdnlibs.org/api"
"""Base URL of the lib.social JSON API shared across the network's sites."""

RANOBELIB_SITE_ID = "3"
"""``Site-Id`` header value that scopes requests to ranobelib.me. See docs/api-notes.md."""


class ApiClient:
    """Thin async wrapper around the undocumented api.cdnlibs.org JSON API."""

    def __init__(
        self,
        *,
        base_url: str = API_BASE_URL,
        timeout: float = 15.0,
        transport: httpx.AsyncBaseTransport | None = None,
    ) -> None:
        self._http = httpx.AsyncClient(
            base_url=base_url,
            timeout=timeout,
            transport=transport,
            headers={
                "Site-Id": RANOBELIB_SITE_ID,
                "Accept": "application/json",
            },
        )

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
        response = await self._http.get(f"/manga/{slug_url}", params=params)
        self._raise_for_status(response, slug_url=slug_url)
        data: dict[str, Any] = response.json()["data"]
        return data

    def _raise_for_status(self, response: httpx.Response, *, slug_url: str) -> None:
        if response.status_code == 404:
            raise TitleNotFoundError(slug_url)
        if response.status_code == 403:
            raise AuthRequiredError(str(response.request.url))
        if response.status_code == 429:
            retry_after = response.headers.get("Retry-After")
            raise RateLimitError(float(retry_after) if retry_after else None)
        try:
            response.raise_for_status()
        except httpx.HTTPStatusError as exc:
            raise RanobeLibError(f"Unexpected API response: {exc}") from exc
