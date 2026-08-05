"""Unit tests for ranobelib.client.ApiClient, using a mock transport (no network)."""

from collections.abc import Callable

import httpx
import pytest

from ranobelib.client import ApiClient
from ranobelib.exceptions import (
    AuthRequiredError,
    RanobeLibError,
    RateLimitError,
    TitleNotFoundError,
)


def _client(handler: Callable[[httpx.Request], httpx.Response]) -> ApiClient:
    return ApiClient(transport=httpx.MockTransport(handler))


async def test_get_title_returns_data_payload() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        assert request.url.path == "/api/manga/1--example"
        assert request.headers["Site-Id"] == "3"
        assert request.headers["Accept"] == "application/json"
        return httpx.Response(200, json={"data": {"id": 1, "name": "Example"}})

    async with _client(handler) as client:
        data = await client.get_title("1--example")

    assert data == {"id": 1, "name": "Example"}


async def test_get_title_sends_requested_fields_as_query_params() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        assert request.url.params.get_list("fields[]") == ["summary", "genres"]
        return httpx.Response(200, json={"data": {}})

    async with _client(handler) as client:
        await client.get_title("1--example", fields=["summary", "genres"])


async def test_get_title_raises_title_not_found_on_404() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(404, json={"data": {"toast": {"message": "Not Found"}}})

    async with _client(handler) as client:
        with pytest.raises(TitleNotFoundError) as exc_info:
            await client.get_title("1--missing")

    assert exc_info.value.slug_url == "1--missing"


async def test_get_title_raises_auth_required_on_403() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(403, json={"data": {}})

    async with _client(handler) as client:
        with pytest.raises(AuthRequiredError):
            await client.get_title("1--paywalled")


async def test_get_title_raises_rate_limit_error_on_429_with_retry_after() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(429, headers={"Retry-After": "30"}, json={"data": {}})

    async with _client(handler) as client:
        with pytest.raises(RateLimitError) as exc_info:
            await client.get_title("1--throttled")

    assert exc_info.value.retry_after == 30.0


async def test_get_title_raises_rate_limit_error_on_429_without_retry_after() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(429, json={"data": {}})

    async with _client(handler) as client:
        with pytest.raises(RateLimitError) as exc_info:
            await client.get_title("1--throttled")

    assert exc_info.value.retry_after is None


async def test_get_title_wraps_other_error_statuses_in_ranobelib_error() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(500, text="internal error")

    async with _client(handler) as client:
        with pytest.raises(RanobeLibError):
            await client.get_title("1--broken")


async def test_get_chapters_returns_data_array() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        assert request.url.path == "/api/manga/1--example/chapters"
        assert request.headers["Site-Id"] == "3"
        return httpx.Response(200, json={"data": [{"id": 1, "volume": "1", "number": "1"}]})

    async with _client(handler) as client:
        data = await client.get_chapters("1--example")

    assert data == [{"id": 1, "volume": "1", "number": "1"}]


async def test_get_chapters_raises_title_not_found_on_404() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(404, json={"data": {"toast": {"message": "Not Found"}}})

    async with _client(handler) as client:
        with pytest.raises(TitleNotFoundError):
            await client.get_chapters("1--missing")


async def test_aclose_without_context_manager() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(200, json={"data": {}})

    client = _client(handler)
    await client.get_title("1--example")
    await client.aclose()
