from __future__ import annotations
import itertools
from operator import attrgetter
from typing import TypedDict
from harvester.models import EventSummary, EventType, StreamEvent, UserAggregate
from harvester.parser import format_amsterdam_time


class BonusStats(TypedDict):
    successful_streams_per_user: dict[int, int]
    sytflix_started_stream_percentage: float | None


class HarvestResult(TypedDict):
    users: list[dict]
    shows_released_2020_or_later: int
    duration_ms: int
    bonus: BonusStats



def aggregate(events: list[StreamEvent]) -> HarvestResult:
    """Build the final output structure from collected events."""
    sorted_events = sorted(events, key=attrgetter("user.id", "event_date_amsterdam"))

    user_aggregates = [
        _aggregate_user(uid, list(user_events))
        for uid, user_events in itertools.groupby(sorted_events, key=attrgetter("user.id"))
    ]

    return HarvestResult(
        users=[_serialise_user(u) for u in user_aggregates],
        shows_released_2020_or_later=_count_shows_released_since_2020(events),
        duration_ms=0,  # filled by orchestrator
        bonus=BonusStats(
            successful_streams_per_user={
                u.user_id: u.successful_streams for u in user_aggregates
            },
            sytflix_started_stream_percentage=_sytflix_started_pct(events),
        ),
    )



def _aggregate_user(user_id: int, events: list[StreamEvent]) -> UserAggregate:
    first = events[0]
    agg = UserAggregate(
        user_id=user_id,
        name=first.user.first_name,
        surname=first.user.last_name,
        age=first.user.age,
    )

    agg.events = [
        EventSummary(
            event_type=ev.event_type.value,
            platform=ev.platform,
            show_title=ev.show.title,
            first_cast_member=ev.show.first_cast_member,
            show_id=ev.show.show_id,
            event_time=format_amsterdam_time(ev.event_date_amsterdam),
        )
        for ev in events
    ]

    agg.successful_streams = _count_successful_streams(events)
    return agg


def _serialise_user(u: UserAggregate) -> dict:
    return {
        "user_id": u.user_id,
        "name": u.name,
        "surname": u.surname,
        "age": u.age,
        "successful_streams": u.successful_streams,
        "events": [
            {
                "event_type": e.event_type,
                "platform": e.platform,
                "show_title": e.show_title,
                "first_cast_member": e.first_cast_member,
                "show_id": e.show_id,
                "event_time_amsterdam": e.event_time,
            }
            for e in u.events
        ],
    }


def _count_shows_released_since_2020(events: list[StreamEvent]) -> int:

    seen: dict[str, int] = {}
    for ev in events:
        seen.setdefault(ev.show.show_id, ev.show.release_year)
    return sum(1 for year in seen.values() if year >= 2020)


def _count_successful_streams(sorted_events: list[StreamEvent]) -> int:
    return sum(
        curr.event_type is EventType.STREAM_STARTED
        and nxt.event_type.is_stream_end
        and curr.show.show_id == nxt.show.show_id
        and curr.platform == nxt.platform
        for curr, nxt in itertools.pairwise(sorted_events)
    )


def _sytflix_started_pct(events: list[StreamEvent]) -> float | None:
    sytflix = [e for e in events if e.platform.lower() == "sytflix"]
    if not sytflix:
        return None
    started = sum(1 for e in sytflix if e.event_type is EventType.STREAM_STARTED)
    return round(started / len(sytflix) * 100, 2)
