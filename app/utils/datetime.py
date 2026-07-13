from datetime import UTC, date, datetime, timedelta

from app.core.config import settings


def get_current_datetime() -> datetime:
    return datetime.now(settings.timezone)


def get_current_date() -> date:
    return get_current_datetime().date()


def get_recent_start_date(days: int) -> date:
    return get_current_date() - timedelta(days=days - 1)


def get_current_utc_datetime() -> datetime:
    return datetime.now(UTC)


def today_local() -> date:
    return get_current_date()


def now_local() -> datetime:
    return get_current_datetime()
