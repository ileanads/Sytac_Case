
from __future__ import annotations


class HarvesterError(Exception):
    """Base exception for all harvester errors."""


class StreamConnectionError(HarvesterError):
    def __init__(self, platform: str, cause: Exception | None = None) -> None:
        self.platform = platform
        self.cause = cause
        super().__init__(f"Failed to connect to {platform}: {cause}")


class EventParseError(HarvesterError):

    def __init__(self, platform: str, reason: str) -> None:
        self.platform = platform
        self.reason = reason
        super().__init__(f"Parse error on {platform}: {reason}")
