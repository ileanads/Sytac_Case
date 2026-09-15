from __future__ import annotations
import asyncio
import logging
from collections.abc import AsyncIterator
from functools import wraps
from typing import Callable, TypeVar
import httpx
from httpx_sse import aconnect_sse
from harvester.config import BASE_URL, PASSWORD, USERNAME
from harvester.exceptions import StreamConnectionError
from harvester.models import StreamEvent
from harvester.parser import parse_event

logger = logging.getLogger(__name__)

F = TypeVar("F", bound=Callable)


def retry(max_attempts: int = 3, backoff_base: float = 1.0):
    def decorator(func: F) -> F:
        @wraps(func)
        async def wrapper(*args, **kwargs):
            last_exc: Exception | None = None
            for attempt in range(1, max_attempts + 1):
                try:
                    return await func(*args, **kwargs)
                except httpx.ConnectError as exc:
                    last_exc = exc
                    if attempt < max_attempts:
                        wait = backoff_base * (2 ** (attempt - 1))
                        logger.warning(
                            "Connection failed (attempt %d/%d), retrying in %.1fs...",
                            attempt, max_attempts, wait,
                        )
                        await asyncio.sleep(wait)
            raise StreamConnectionError(
                platform=args[0] if args else "unknown",
                cause=last_exc,
            )
        return wrapper
    return decorator


async def event_stream(
    platform: str,
    stop_event: asyncio.Event,
) -> AsyncIterator[StreamEvent]:

    url = f"{BASE_URL}/{platform}"
    auth = (USERNAME, PASSWORD)

    async with httpx.AsyncClient(timeout=None, auth=auth) as client:
        async with aconnect_sse(client, "GET", url) as source:
            async for sse in source.aiter_sse():
                if stop_event.is_set():
                    return

                event = parse_event(sse.event, sse.data, platform)
                if event is not None:
                    yield event


@retry(max_attempts=3, backoff_base=0.5)
async def consume_stream(
    platform: str,
    on_event: Callable[[StreamEvent], None],
    stop_event: asyncio.Event,
) -> None:
    try:
        async for event in event_stream(platform, stop_event):
            on_event(event)
            if stop_event.is_set():
                return

    except StreamConnectionError:
        logger.error(
            "Could not connect to %s after retries — is the Docker server running?",
            platform,
        )
    except httpx.HTTPStatusError as exc:
        logger.error("HTTP error on %s: %s", platform, exc)
    except Exception as exc:  # noqa: BLE001
        if not stop_event.is_set():
            logger.error("Unexpected error on %s: %s", platform, exc)
