from datetime import UTC, date, datetime, timedelta


def utc_now() -> datetime:
    return datetime.now(UTC)


def today_local() -> date:
    return date.today()


def date_days_ago(days: int) -> date:
    return today_local() - timedelta(days=days)
