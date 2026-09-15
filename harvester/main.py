from __future__ import annotations

import argparse
import asyncio
import json
import logging
import time
from contextlib import asynccontextmanager
from collections.abc import AsyncIterator
from pathlib import Path
from typing import Protocol

from harvester.aggregator import HarvestResult, aggregate
from harvester.config import PLATFORMS, SYTAC_DETECTION_LIMIT, TIMEOUT_SECONDS
from harvester.consumer import consume_stream
from harvester.models import StreamEvent

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
logger = logging.getLogger(__name__)


class EventHandler(Protocol):
    def __call__(self, event: StreamEvent) -> None: ...


class Harvester:
    def __init__(self, timeout: int = TIMEOUT_SECONDS) -> None:
        self.events: list[StreamEvent] = []
        self.sytac_count: int = 0
        self.stop_event: asyncio.Event = asyncio.Event()
        self._timeout = timeout

    def on_event(self, event: StreamEvent) -> None:
        self.events.append(event)

        if event.user.first_name == "Sytac":
            self.sytac_count += 1
            logger.info(
                "Sytac user detected (%d/%d) on %s",
                self.sytac_count,
                SYTAC_DETECTION_LIMIT,
                event.platform,
            )
            if self.sytac_count >= SYTAC_DETECTION_LIMIT:
                logger.info("Sytac detection limit reached — stopping all streams.")
                self.stop_event.set()

    @asynccontextmanager
    async def session(self) -> AsyncIterator[Harvester]:
        start_ns = time.monotonic_ns()

        async def _timeout_guard() -> None:
            await asyncio.sleep(self._timeout)
            if not self.stop_event.is_set():
                logger.info("Timeout of %ds reached — stopping all streams.", self._timeout)
                self.stop_event.set()

        try:
            async with asyncio.TaskGroup() as tg:
                for platform in PLATFORMS:
                    tg.create_task(
                        consume_stream(platform, self.on_event, self.stop_event)
                    )
                tg.create_task(_timeout_guard())

        except* Exception as eg:
            for exc in eg.exceptions:
                logger.error("Task failed: %s", exc)

        self._duration_ms = (time.monotonic_ns() - start_ns) // 1_000_000
        logger.info(
            "Harvesting complete: %d events in %d ms.",
            len(self.events),
            self._duration_ms,
        )

        yield self

    def result(self) -> HarvestResult:
        """Aggregate collected events into the final output structure."""
        output = aggregate(self.events)
        output["duration_ms"] = getattr(self, "_duration_ms", 0)
        return output

def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Sytac streaming data harvester",
        formatter_class=argparse.ArgumentDefaultsHelpFormatter,
    )
    parser.add_argument(
        "-o", "--output",
        default="output.json",
        help="Path for the JSON output file",
    )
    parser.add_argument(
        "-t", "--timeout",
        type=int,
        default=TIMEOUT_SECONDS,
        help="Seconds before stopping",
    )
    parser.add_argument(
        "-q", "--quiet",
        action="store_true",
        help="Suppress stdout output (write to file only)",
    )
    return parser.parse_args()


async def _async_main(args: argparse.Namespace) -> None:
    harvester = Harvester(timeout=args.timeout)

    async with harvester.session():
        result = harvester.result()

    output_json = json.dumps(result, indent=2, ensure_ascii=False)

    Path(args.output).write_text(output_json, encoding="utf-8")
    logger.info("Results written to %s", args.output)

    if not args.quiet:
        print(output_json)


def main() -> None:
    args = parse_args()
    asyncio.run(_async_main(args))


if __name__ == "__main__":
    main()
