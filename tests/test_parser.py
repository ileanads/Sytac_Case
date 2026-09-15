import json
from datetime import datetime
from zoneinfo import ZoneInfo

import pytest

from harvester.models import EventType
from harvester.parser import convert_to_amsterdam, format_amsterdam_time, parse_event

AMS = ZoneInfo("Europe/Amsterdam")


class TestConvertToAmsterdam:
    """Verify timezone conversion for every country in the mapping + default."""

    @pytest.mark.parametrize("country,input_hour,expected_hour", [
        ("NL", 12, 12),
        ("DE", 12, 12),
        ("PT", 10, 11),
        ("US", 12, 21),
        ("CA", 6, 12), 
        ("RU", 15, 13),
        ("ID", 18, 12), 
        ("CN", 20, 13),
    ])
    def test_winter_conversions(self, country: str, input_hour: int, expected_hour: int):
        dt = convert_to_amsterdam(f"15-01-2023 {input_hour:02d}:00:00.000", country)
        assert dt.hour == expected_hour
        assert dt.tzinfo is not None

    def test_preserves_milliseconds(self):
        dt = convert_to_amsterdam("15-01-2023 12:30:45.678", "NL")
        assert dt.microsecond == 678000


class TestParseEvent:
    VALID_PAYLOAD = json.dumps({
        "show": {
            "show_id": "s41", "cast": "Alice Smith, Bob Jones",
            "country": "United States", "date_added": "July 16, 2021",
            "description": "A great show.", "director": "Jane Doe",
            "duration": "3 Seasons", "listed_in": "Drama", "rating": "TV-PG",
            "release_year": 2021, "title": "Test Show", "type": "Movie",
            "platform": "Sytflix",
        },
        "event_date": "27-02-2023 03:20:17.111",
        "user": {
            "id": 42, "date_of_birth": "31/10/1990", "email": "test@example.com",
            "first_name": "Elena", "gender": "Female", "ip_address": "1.2.3.4",
            "country": "NL", "last_name": "Doe",
        },
    })

    def test_valid_event(self):
        ev = parse_event("show-liked", self.VALID_PAYLOAD, "sytflix")
        assert ev is not None
        assert ev.event_type is EventType.SHOW_LIKED
        assert ev.user.first_name == "Elena"
        assert ev.show.show_id == "s41"
        assert ev.show.first_cast_member == "Alice Smith"
        assert ev.platform == "Sytflix"

    def test_unknown_event_type(self):
        ev = parse_event("brand-new-event", self.VALID_PAYLOAD, "sytflix")
        assert ev is not None
        assert ev.event_type is EventType.UNKNOWN

    def test_malformed_json(self):
        assert parse_event("x", "not json{{{", "sytflix") is None

    def test_missing_show_key(self):
        payload = json.dumps({"user": {"id": 1}, "event_date": "01-01-2023 00:00:00.000"})
        assert parse_event("x", payload, "sytflix") is None

    def test_missing_user_key(self):
        payload = json.dumps({"show": {"show_id": "s1"}, "event_date": "01-01-2023 00:00:00.000"})
        assert parse_event("x", payload, "sytflix") is None

    def test_platform_falls_back_to_endpoint(self):
        payload = json.dumps({
            "show": {"show_id": "s1", "release_year": 2020, "cast": "", "title": "X"},
            "event_date": "01-01-2023 00:00:00.000",
            "user": {"id": 1, "first_name": "A", "last_name": "B",
                     "date_of_birth": "01/01/1990", "country": "NL"},
        })
        ev = parse_event("stream-started", payload, "sytflix")
        assert ev is not None
        assert ev.platform == "sytflix"

    def test_non_dict_show_rejected(self):
        """Guard against show/user being a string or list instead of an object."""
        payload = json.dumps({
            "show": "not a dict",
            "event_date": "01-01-2023 00:00:00.000",
            "user": {"id": 1, "first_name": "A", "last_name": "B",
                     "date_of_birth": "01/01/1990", "country": "NL"},
        })
        assert parse_event("x", payload, "sytflix") is None


class TestFormatAmsterdamTime:
    def test_millisecond_precision(self):
        dt = datetime(2023, 2, 27, 3, 20, 17, 111000, tzinfo=AMS)
        assert format_amsterdam_time(dt) == "27-02-2023 03:20:17.111"

    def test_truncates_microseconds(self):
        dt = datetime(2023, 1, 1, 0, 0, 0, 123456, tzinfo=AMS)
        assert format_amsterdam_time(dt).endswith(".123")

    def test_zero_microseconds(self):
        dt = datetime(2023, 1, 1, 0, 0, 0, 0, tzinfo=AMS)
        assert format_amsterdam_time(dt).endswith(".000")
