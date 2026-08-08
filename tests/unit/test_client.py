"""Unit tests for ranobelib.client.ApiClient, using a mock transport (no network)."""

import asyncio
from collections.abc import Callable
from typing import Any

import httpx
import pytest

from ranobelib.client import ApiClient
from ranobelib.exceptions import (
    AuthRequiredError,
    ChapterNotFoundError,
    RanobeLibError,
    RateLimitError,
    TitleNotFoundError,
)


async def _no_sleep(delay: float) -> None:
    """Stand-in for asyncio.sleep in tests: skips real waiting for pacing/backoff delays."""


def _client(handler: Callable[[httpx.Request], httpx.Response], **kwargs: Any) -> ApiClient:
    kwargs.setdefault("sleep", _no_sleep)
    return ApiClient(transport=httpx.MockTransport(handler), **kwargs)


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


async def test_get_chapter_sends_number_and_volume_query_params() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        assert request.url.path == "/api/manga/1--example/chapter"
        assert request.url.params["number"] == "51.6"
        assert request.url.params["volume"] == "6"
        assert "branch_id" not in request.url.params
        return httpx.Response(200, json={"data": {"id": 1, "content": "<p>Hi.</p>"}})

    async with _client(handler) as client:
        data = await client.get_chapter("1--example", number="51.6", volume="6")

    assert data == {"id": 1, "content": "<p>Hi.</p>"}


async def test_get_chapter_sends_branch_id_when_given() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        assert request.url.params["branch_id"] == "2251"
        return httpx.Response(200, json={"data": {}})

    async with _client(handler) as client:
        await client.get_chapter("1--example", number="1", volume="1", branch_id=2251)


async def test_get_chapter_raises_chapter_not_found_on_404() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(404, json={"data": {"toast": {"message": "Not Found"}}})

    async with _client(handler) as client:
        with pytest.raises(ChapterNotFoundError) as exc_info:
            await client.get_chapter("1--example", number="9999", volume="999")

    assert exc_info.value.slug_url == "1--example"
    assert exc_info.value.volume == "999"
    assert exc_info.value.number == "9999"


async def test_get_chapter_raises_auth_required_on_403() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(403, json={"data": {}})

    async with _client(handler) as client:
        with pytest.raises(AuthRequiredError):
            await client.get_chapter("1--example", number="1", volume="1")


async def test_list_titles_sends_expected_query_params() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        assert request.url.path == "/api/manga"
        assert request.url.params.get_list("site_id[]") == ["3"]
        assert request.url.params["page"] == "1"
        assert request.url.params["limit"] == "30"
        assert request.url.params["sort_by"] == "last_chapter_at"
        assert request.url.params["q"] == "dxd"
        assert request.url.params.get_list("genres[]") == ["34", "35"]
        assert request.url.params.get_list("status[]") == ["1"]
        return httpx.Response(200, json={"data": [], "meta": {}})

    async with _client(handler) as client:
        await client.list_titles(
            page=1,
            per_page=30,
            query="dxd",
            genres=[34, 35],
            status=1,
            sort="last_chapter_at",
        )


async def test_list_titles_omits_optional_params_when_not_given() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        assert "q" not in request.url.params
        assert "genres[]" not in request.url.params
        assert "status[]" not in request.url.params
        return httpx.Response(200, json={"data": [], "meta": {}})

    async with _client(handler) as client:
        await client.list_titles(
            page=1, per_page=30, query=None, genres=None, status=None, sort="name"
        )


async def test_list_titles_returns_full_response_body() -> None:
    payload = {"data": [{"id": 1}], "meta": {"current_page": 1, "has_next_page": True}}

    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(200, json=payload)

    async with _client(handler) as client:
        result = await client.list_titles(
            page=1, per_page=30, query=None, genres=None, status=None, sort="name"
        )

    assert result == payload


async def test_list_titles_raises_rate_limit_error_on_429() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(429, json={"data": {}})

    async with _client(handler) as client:
        with pytest.raises(RateLimitError):
            await client.list_titles(
                page=1, per_page=30, query=None, genres=None, status=None, sort="name"
            )


async def test_list_titles_wraps_validation_error_in_ranobelib_error() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(422, json={"data": {"sort_by": ["The selected sort_by is invalid."]}})

    async with _client(handler) as client:
        with pytest.raises(RanobeLibError):
            await client.list_titles(
                page=1, per_page=30, query=None, genres=None, status=None, sort="bogus"
            )


async def test_aclose_without_context_manager() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(200, json={"data": {}})

    client = _client(handler)
    await client.get_title("1--example")
    await client.aclose()


async def test_get_title_retries_on_429_then_succeeds() -> None:
    responses = iter(
        [
            httpx.Response(429, headers={"Retry-After": "5"}, json={"data": {}}),
            httpx.Response(200, json={"data": {"id": 1}}),
        ]
    )

    def handler(request: httpx.Request) -> httpx.Response:
        return next(responses)

    async with _client(handler) as client:
        data = await client.get_title("1--example")

    assert data == {"id": 1}


async def test_get_title_retries_on_5xx_then_succeeds() -> None:
    responses = iter(
        [httpx.Response(503, text="unavailable"), httpx.Response(200, json={"data": {}})]
    )

    def handler(request: httpx.Request) -> httpx.Response:
        return next(responses)

    async with _client(handler) as client:
        await client.get_title("1--example")  # Doesn't raise.


async def test_get_title_gives_up_after_max_retries() -> None:
    attempts = 0

    def handler(request: httpx.Request) -> httpx.Response:
        nonlocal attempts
        attempts += 1
        return httpx.Response(429, json={"data": {}})

    async with _client(handler, max_retries=2) as client:
        with pytest.raises(RateLimitError):
            await client.get_title("1--example")

    assert attempts == 3  # Initial attempt plus 2 retries.


async def test_retry_backoff_doubles_and_honors_retry_after() -> None:
    delays: list[float] = []

    async def recording_sleep(delay: float) -> None:
        delays.append(delay)

    responses = iter(
        [
            httpx.Response(500, text="a"),
            httpx.Response(500, text="b"),
            httpx.Response(429, headers={"Retry-After": "9"}, json={"data": {}}),
            httpx.Response(200, json={"data": {}}),
        ]
    )

    def handler(request: httpx.Request) -> httpx.Response:
        return next(responses)

    async with _client(
        handler, sleep=recording_sleep, max_retries=3, retry_base_delay=1.0, request_delay=0.0
    ) as client:
        await client.get_title("1--example")

    assert delays == [1.0, 2.0, 9.0]


async def test_retry_backoff_ignores_unparseable_retry_after() -> None:
    delays: list[float] = []

    async def recording_sleep(delay: float) -> None:
        delays.append(delay)

    responses = iter(
        [
            httpx.Response(429, headers={"Retry-After": "not-a-number"}, json={"data": {}}),
            httpx.Response(200, json={"data": {}}),
        ]
    )

    def handler(request: httpx.Request) -> httpx.Response:
        return next(responses)

    async with _client(handler, sleep=recording_sleep, retry_base_delay=1.0) as client:
        await client.get_title("1--example")

    assert delays == [1.0]


async def test_pace_waits_for_request_delay_between_calls() -> None:
    delays: list[float] = []

    async def recording_sleep(delay: float) -> None:
        delays.append(delay)

    clock_values = iter([0.0, 0.0, 0.15, 0.15])

    def fake_clock() -> float:
        return next(clock_values)

    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(200, json={"data": {}})

    async with _client(
        handler, sleep=recording_sleep, clock=fake_clock, request_delay=0.2
    ) as client:
        await client.get_title("1--a")
        await client.get_title("1--b")

    assert delays == [pytest.approx(0.05)]


async def test_max_concurrency_limits_in_flight_requests() -> None:
    in_flight = 0
    max_in_flight = 0
    lock = asyncio.Lock()

    async def handler(request: httpx.Request) -> httpx.Response:
        nonlocal in_flight, max_in_flight
        async with lock:
            in_flight += 1
            max_in_flight = max(max_in_flight, in_flight)
        await asyncio.sleep(0.05)
        async with lock:
            in_flight -= 1
        return httpx.Response(200, json={"data": {}})

    async with _client(handler, max_concurrency=2, request_delay=0.0) as client:
        await asyncio.gather(*(client.get_title(f"{i}--x") for i in range(5)))

    assert max_in_flight == 2
