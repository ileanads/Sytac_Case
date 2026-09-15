from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date, datetime
from enum import Enum, auto
from functools import lru_cache
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from collections.abc import Sequence


class EventType(Enum):
    STREAM_STARTED = "stream-started"
    STREAM_ENDED = "stream-ended"
    STREAM_FINISHED = "stream-finished"
    STREAM_INTERRUPTED = "stream-interrupted"
    SHOW_LIKED = "show-liked"
    UNKNOWN = "unknown"

    @classmethod
    def from_str(cls, value: str) -> EventType:
        try:
            return cls(value)
        except ValueError:
            return cls.UNKNOWN

    @property
    def is_stream_end(self) -> bool:
        return self in (EventType.STREAM_ENDED, EventType.STREAM_FINISHED)


@dataclass(frozen=True, slots=True)
class Show:
    show_id: str
    title: str
    cast: str
    release_year: int
    platform: str
    country: str = ""
    date_added: str = ""
    description: str = ""
    director: str = ""
    duration: str = ""
    listed_in: str = ""
    rating: str = ""
    show_type: str = ""

    @property
    def first_cast_member(self) -> str | None:
        return _first_cast(self.cast) if self.cast else None


@lru_cache(maxsize=256)
def _first_cast(cast_str: str) -> str | None:
    name = cast_str.split(",", maxsplit=1)[0].strip()
    return name or None


@dataclass(frozen=True, slots=True)
class User:
    id: int
    first_name: str
    last_name: str
    date_of_birth: str
    email: str = ""
    gender: str = ""
    ip_address: str = ""
    country: str = ""

    @property
    def full_name(self) -> str:
        return f"{self.first_name} {self.last_name}"

    @property
    def age(self) -> int | None:
        return _compute_age(self.date_of_birth)


@lru_cache(maxsize=256)
def _compute_age(dob_str: str) -> int | None:
    try:
        dob = datetime.strptime(dob_str, "%d/%m/%Y").date()
        today = date.today()
        return today.year - dob.year - (
            (today.month, today.day) < (dob.month, dob.day)
        )
    except (ValueError, TypeError):
        return None


@dataclass(frozen=True, slots=True)
class StreamEvent:
    event_type: EventType
    event_date_amsterdam: datetime
    show: Show
    user: User
    platform: str

    def __post_init__(self) -> None:
        if self.event_date_amsterdam.tzinfo is None:
            raise ValueError("event_date_amsterdam must be timezone-aware")


@dataclass(slots=True)
class UserAggregate:

    user_id: int
    name: str
    surname: str
    age: int | None
    events: list[EventSummary] = field(default_factory=list)
    successful_streams: int = 0


@dataclass(frozen=True, slots=True)
class EventSummary:
    event_type: str
    platform: str
    show_title: str
    first_cast_member: str | None
    show_id: str
    event_time: str
