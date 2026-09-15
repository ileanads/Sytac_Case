from __future__ import annotations

import json
import logging
from datetime import datetime
from typing import TypeAlias

from harvester.config import AMSTERDAM_TZ, COUNTRY_TIMEZONES, EVENT_DATE_FORMAT
from harvester.models import EventType, Show, StreamEvent, User

logger = logging.getLogger(__name__)

RawEventData: TypeAlias = dict[str, object]


def convert_to_amsterdam(event_date_str: str, user_country: str) -> datetime:
    naive_dt = datetime.strptime(event_date_str.strip(), EVENT_DATE_FORMAT)
    source_tz = COUNTRY_TIMEZONES.get(user_country, AMSTERDAM_TZ)
    return naive_dt.replace(tzinfo=source_tz).astimezone(AMSTERDAM_TZ)


def parse_event(event_type: str, data_json: str, platform: str) -> StreamEvent | None:

    try:
        payload: RawEventData = json.loads(data_json)
    except json.JSONDecodeError:
        logger.debug("Skipping malformed JSON on %s", platform)
        return None

    try:
        show_data = payload["show"]
        user_data = payload["user"]

        if not isinstance(show_data, dict) or not isinstance(user_data, dict):
            raise TypeError("show and user must be objects")

        show = _build_show(show_data, platform)
        user = _build_user(user_data)

        event_date_amsterdam = convert_to_amsterdam(
            str(payload["event_date"]), user.country
        )

        return StreamEvent(
            event_type=EventType.from_str(event_type),
            event_date_amsterdam=event_date_amsterdam,
            show=show,
            user=user,
            platform=show.platform,
        )

    except (KeyError, ValueError, TypeError) as exc:
        logger.debug("Skipping malformed event on %s: %s", platform, exc)
        return None


def _build_show(data: dict, fallback_platform: str) -> Show:
    return Show(
        show_id=str(data["show_id"]),
        title=data.get("title", ""),
        cast=data.get("cast", ""),
        release_year=int(data.get("release_year", 0)),
        platform=data.get("platform", fallback_platform),
        country=data.get("country", ""),
        date_added=data.get("date_added", ""),
        description=data.get("description", ""),
        director=data.get("director", ""),
        duration=data.get("duration", ""),
        listed_in=data.get("listed_in", ""),
        rating=data.get("rating", ""),
        show_type=data.get("type", ""),
    )


def _build_user(data: dict) -> User:
    return User(
        id=int(data["id"]),
        first_name=data.get("first_name", ""),
        last_name=data.get("last_name", ""),
        date_of_birth=data.get("date_of_birth", ""),
        email=data.get("email", ""),
        gender=data.get("gender", ""),
        ip_address=data.get("ip_address", ""),
        country=data.get("country", ""),
    )


def format_amsterdam_time(dt: datetime) -> str:
    return dt.strftime("%d-%m-%Y %H:%M:%S.") + f"{dt.microsecond // 1000:03d}"
