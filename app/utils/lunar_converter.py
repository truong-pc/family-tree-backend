from datetime import date
from typing import Optional
from lunar_python import Solar


def solar_to_lunar(dod: Optional[date]) -> Optional[dict]:
    """
    Convert a solar (Gregorian) date of death to lunar calendar fields.
    Returns dict with lunarDeathDay, lunarDeathMonth, lunarDeathYear, lunarIsLeap
    or None if dod is None.

    In lunar-python, getMonth() returns a negative value for leap months.
    E.g. -6 means leap month 6. We extract the absolute month and set lunarIsLeap=True.
    """
    if dod is None:
        return None

    solar = Solar.fromYmd(dod.year, dod.month, dod.day)
    lunar = solar.getLunar()

    raw_month = lunar.getMonth()
    is_leap = raw_month < 0
    month = abs(raw_month)

    return {
        "lunarDeathDay": lunar.getDay(),
        "lunarDeathMonth": month,
        "lunarDeathYear": lunar.getYear(),
        "lunarIsLeap": is_leap,
    }
