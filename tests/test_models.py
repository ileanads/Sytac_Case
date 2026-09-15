import pytest

from harvester.models import EventType, Show, StreamEvent, User


class TestEventType:
    def test_from_str_known(self):
        assert EventType.from_str("stream-started") is EventType.STREAM_STARTED
        assert EventType.from_str("stream-finished") is EventType.STREAM_FINISHED

    def test_from_str_unknown(self):
        assert EventType.from_str("some-new-event") is EventType.UNKNOWN

    def test_is_stream_end(self):
        assert EventType.STREAM_ENDED.is_stream_end is True
        assert EventType.STREAM_FINISHED.is_stream_end is True
        assert EventType.STREAM_STARTED.is_stream_end is False
        assert EventType.SHOW_LIKED.is_stream_end is False


class TestShow:
    def test_first_cast_member(self):
        show = Show(show_id="s1", title="X", cast="Alice, Bob, Charlie", release_year=2021, platform="Sytflix")
        assert show.first_cast_member == "Alice"

    def test_first_cast_member_empty(self):
        show = Show(show_id="s1", title="X", cast="", release_year=2021, platform="Sytflix")
        assert show.first_cast_member is None

    def test_first_cast_member_single(self):
        show = Show(show_id="s1", title="X", cast="Solo Actor", release_year=2021, platform="Sytflix")
        assert show.first_cast_member == "Solo Actor"

    def test_first_cast_member_whitespace(self):
        show = Show(show_id="s1", title="X", cast="  Alice , Bob", release_year=2021, platform="Sytflix")
        assert show.first_cast_member == "Alice"

    def test_first_cast_member_cached(self):
        """cached_property should return the same object on repeated access."""
        show = Show(show_id="s1", title="X", cast="Alice, Bob", release_year=2021, platform="P")
        assert show.first_cast_member is show.first_cast_member


class TestUser:
    def test_full_name(self):
        user = User(id=1, first_name="Elena", last_name="Crudu", date_of_birth="15/06/1995")
        assert user.full_name == "Elena Crudu"

    def test_age_calculation(self):
        user = User(id=1, first_name="A", last_name="B", date_of_birth="01/01/2000")
        assert user.age is not None
        assert 24 <= user.age <= 30

    def test_age_invalid_dob(self):
        user = User(id=1, first_name="A", last_name="B", date_of_birth="not-a-date")
        assert user.age is None

    def test_age_empty_dob(self):
        user = User(id=1, first_name="A", last_name="B", date_of_birth="")
        assert user.age is None

    def test_immutability(self):
        """Frozen dataclasses reject attribute mutation."""
        show = Show(show_id="s1", title="X", cast="", release_year=2021, platform="P")
        with pytest.raises(AttributeError):
            show.title = "Y"


class TestStreamEvent:
    def test_rejects_naive_datetime(self):
        """StreamEvent.__post_init__ should reject timezone-naive datetimes."""
        from datetime import datetime
        with pytest.raises(ValueError, match="timezone-aware"):
            StreamEvent(
                event_type=EventType.SHOW_LIKED,
                event_date_amsterdam=datetime(2023, 1, 1),  # naive!
                show=Show(show_id="s1", title="X", cast="", release_year=2021, platform="P"),
                user=User(id=1, first_name="A", last_name="B", date_of_birth="01/01/2000"),
                platform="P",
            )
