from __future__ import annotations

from zoneinfo import ZoneInfo, available_timezones

BASE_URL = "http://localhost:8080"
USERNAME = "sytac"
PASSWORD = "4p9g-Dv7T-u8fe-iz6y-SRW2"

PLATFORMS: tuple[str, ...] = ("sytflix", "sytazon", "sysney")

TIMEOUT_SECONDS = 20
SYTAC_DETECTION_LIMIT = 3

COUNTRY_TIMEZONES: dict[str, ZoneInfo] = {
    "PT": ZoneInfo("UTC"),
    "CA": ZoneInfo("America/Toronto"),
    "US": ZoneInfo("America/Los_Angeles"),
    "RU": ZoneInfo("Europe/Moscow"),
    "ID": ZoneInfo("Asia/Jakarta"),
    "CN": ZoneInfo("Asia/Shanghai"),
}

AMSTERDAM_TZ = ZoneInfo("Europe/Amsterdam")

_unknown_zones = {
    tz.key for tz in (*COUNTRY_TIMEZONES.values(), AMSTERDAM_TZ)
} - available_timezones()
if _unknown_zones:
    raise ValueError(f"Unknown IANA timezone(s): {sorted(_unknown_zones)}")
del _unknown_zones

EVENT_DATE_FORMAT = "%d-%m-%Y %H:%M:%S.%f"
