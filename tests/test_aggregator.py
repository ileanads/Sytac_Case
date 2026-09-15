from datetime import datetime
from zoneinfo import ZoneInfo

import pytest

from harvester.aggregator import (
    _count_shows_released_since_2020,
    _count_successful_streams,
    _sytflix_started_pct,
    aggregate,
)
from harvester.models import EventType, Show, StreamEvent, User

AMS = ZoneInfo("Europe/Amsterdam")


def _make_event(
    event_type: str | EventType = EventType.SHOW_LIKED,
    show_id: str = "s1",
    platform: str = "Sytflix",
    user_id: int = 1,
    first_name: str = "Alice",
    release_year: int = 2021,
    dt: datetime | None = None,
) -> StreamEvent:
    if dt is None:
        dt = datetime(2023, 1, 1, 12, 0, 0, tzinfo=AMS)
    etype = event_type if isinstance(event_type, EventType) else EventType.from_str(event_type)
    return StreamEvent(
        event_type=etype,
        event_date_amsterdam=dt,
        show=Show(
            show_id=show_id, title="Test", cast="Actor One, Actor Two",
            release_year=release_year, platform=platform,
        ),
        user=User(
            id=user_id, first_name=first_name, last_name="Smith",
            date_of_birth="01/01/1990", country="NL",
        ),
        platform=platform,
    )


class TestCountSuccessfulStreams:
    """Verify every scenario from the assignment spec."""

    @pytest.mark.parametrize("end_type", [EventType.STREAM_ENDED, EventType.STREAM_FINISHED])
    def test_valid_pair(self, end_type: EventType):
        events = [
            _make_event(EventType.STREAM_STARTED, "s1", "Sytflix", dt=datetime(2023, 1, 1, 10, tzinfo=AMS)),
            _make_event(end_type, "s1", "Sytflix", dt=datetime(2023, 1, 1, 11, tzinfo=AMS)),
        ]
        assert _count_successful_streams(events) == 1

    def test_different_platform(self):
        events = [
            _make_event(EventType.STREAM_STARTED, "s1", "Sytflix", dt=datetime(2023, 1, 1, 10, tzinfo=AMS)),
            _make_event(EventType.STREAM_ENDED, "s1", "Sytazon", dt=datetime(2023, 1, 1, 11, tzinfo=AMS)),
        ]
        assert _count_successful_streams(events) == 0

    def test_different_show(self):
        events = [
            _make_event(EventType.STREAM_STARTED, "s1", "Sytflix", dt=datetime(2023, 1, 1, 10, tzinfo=AMS)),
            _make_event(EventType.STREAM_ENDED, "s2", "Sytflix", dt=datetime(2023, 1, 1, 11, tzinfo=AMS)),
        ]
        assert _count_successful_streams(events) == 0

    def test_event_in_between(self):
        events = [
            _make_event(EventType.STREAM_STARTED, "s1", "Sytflix", dt=datetime(2023, 1, 1, 10, tzinfo=AMS)),
            _make_event(EventType.SHOW_LIKED, "s1", "Sytflix", dt=datetime(2023, 1, 1, 10, 30, tzinfo=AMS)),
            _make_event(EventType.STREAM_ENDED, "s1", "Sytflix", dt=datetime(2023, 1, 1, 11, tzinfo=AMS)),
        ]
        assert _count_successful_streams(events) == 0

    def test_reversed_order(self):
        events = [
            _make_event(EventType.STREAM_ENDED, "s1", "Sytflix", dt=datetime(2023, 1, 1, 10, tzinfo=AMS)),
            _make_event(EventType.STREAM_STARTED, "s1", "Sytflix", dt=datetime(2023, 1, 1, 11, tzinfo=AMS)),
        ]
        assert _count_successful_streams(events) == 0

    def test_multiple_successes(self):
        events = [
            _make_event(EventType.STREAM_STARTED, "s1", "Sytflix", dt=datetime(2023, 1, 1, 10, tzinfo=AMS)),
            _make_event(EventType.STREAM_FINISHED, "s1", "Sytflix", dt=datetime(2023, 1, 1, 11, tzinfo=AMS)),
            _make_event(EventType.STREAM_STARTED, "s2", "Sytazon", dt=datetime(2023, 1, 1, 12, tzinfo=AMS)),
            _make_event(EventType.STREAM_ENDED, "s2", "Sytazon", dt=datetime(2023, 1, 1, 13, tzinfo=AMS)),
        ]
        assert _count_successful_streams(events) == 2

    def test_empty(self):
        assert _count_successful_streams([]) == 0


class TestShowsReleased2020:
    def test_counts_unique_shows(self):
        events = [
            _make_event(show_id="s1", release_year=2021),
            _make_event(show_id="s1", release_year=2021),
            _make_event(show_id="s2", release_year=2020),
            _make_event(show_id="s3", release_year=2019),
        ]
        assert _count_shows_released_since_2020(events) == 2

    def test_none_qualifying(self):
        assert _count_shows_released_since_2020([_make_event(release_year=2018)]) == 0

    def test_empty(self):
        assert _count_shows_released_since_2020([]) == 0


class TestSytflixPct:
    def test_basic_percentage(self):
        events = [
            _make_event(EventType.STREAM_STARTED, platform="Sytflix"),
            _make_event(EventType.SHOW_LIKED, platform="Sytflix"),
            _make_event(EventType.STREAM_STARTED, platform="Sytflix"),
            _make_event(EventType.STREAM_STARTED, platform="Sytazon"),
        ]
        assert _sytflix_started_pct(events) == 66.67

    def test_no_sytflix_events(self):
        assert _sytflix_started_pct([_make_event(platform="Sytazon")]) is None

    def test_all_started(self):
        events = [_make_event(EventType.STREAM_STARTED, platform="Sytflix") for _ in range(5)]
        assert _sytflix_started_pct(events) == 100.0


class TestAggregate:
    def test_groups_by_user(self):
        events = [
            _make_event(user_id=1, first_name="Alice"),
            _make_event(user_id=2, first_name="Bob"),
            _make_event(user_id=1, first_name="Alice"),
        ]
        result = aggregate(events)
        assert len(result["users"]) == 2
        user_1 = next(u for u in result["users"] if u["user_id"] == 1)
        assert len(user_1["events"]) == 2

    def test_empty_events(self):
        result = aggregate([])
        assert result["users"] == []
        assert result["shows_released_2020_or_later"] == 0

    def test_events_sorted_by_time(self):
        events = [
            _make_event(user_id=1, dt=datetime(2023, 1, 1, 14, tzinfo=AMS)),
            _make_event(user_id=1, dt=datetime(2023, 1, 1, 10, tzinfo=AMS)),
        ]
        result = aggregate(events)
        times = [e["event_time_amsterdam"] for e in result["users"][0]["events"]]
        assert times == sorted(times)

    def test_output_has_typed_structure(self):
        """Verify the output matches the HarvestResult TypedDict keys."""
        result = aggregate([_make_event()])
        assert "users" in result
        assert "shows_released_2020_or_later" in result
        assert "duration_ms" in result
        assert "bonus" in result
        assert "successful_streams_per_user" in result["bonus"]
        assert "sytflix_started_stream_percentage" in result["bonus"]
