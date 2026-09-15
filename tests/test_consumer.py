import asyncio

import httpx
import pytest

from harvester.consumer import retry
from harvester.exceptions import StreamConnectionError


class TestRetryDecorator:
    @pytest.mark.asyncio
    async def test_succeeds_on_first_try(self):
        call_count = 0

        @retry(max_attempts=3, backoff_base=0.01)
        async def succeeding_func():
            nonlocal call_count
            call_count += 1
            return "ok"

        result = await succeeding_func()
        assert result == "ok"
        assert call_count == 1

    @pytest.mark.asyncio
    async def test_retries_on_connect_error(self):
        call_count = 0

        @retry(max_attempts=3, backoff_base=0.01)
        async def flaky_func(platform: str):
            nonlocal call_count
            call_count += 1
            if call_count < 3:
                raise httpx.ConnectError("connection refused")
            return "recovered"

        result = await flaky_func("sytflix")
        assert result == "recovered"
        assert call_count == 3

    @pytest.mark.asyncio
    async def test_raises_after_max_attempts(self):
        @retry(max_attempts=2, backoff_base=0.01)
        async def always_fails(platform: str):
            raise httpx.ConnectError("connection refused")

        with pytest.raises(StreamConnectionError) as exc_info:
            await always_fails("sytflix")
        assert exc_info.value.platform == "sytflix"

    @pytest.mark.asyncio
    async def test_non_connect_errors_propagate_immediately(self):
        call_count = 0

        @retry(max_attempts=3, backoff_base=0.01)
        async def type_error_func():
            nonlocal call_count
            call_count += 1
            raise TypeError("not a connect error")

        with pytest.raises(TypeError):
            await type_error_func()
        assert call_count == 1
