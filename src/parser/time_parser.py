"""AIMS time field parser.

Handles all known AIMS DayRepReport time formats:
- HH:MM (e.g. 14:35)
- HHMM  (e.g. 1435)
- H:MM  (e.g. 6:05)
- HMM   (e.g. 605)
- 2400  (midnight, mapped to 00:00)
- Blank / null / placeholder
- Next-day markers (+1, +2)
"""

from __future__ import annotations

from datetime import datetime, time
from typing import Any

import pandas as pd

from src.config import NULL_TIME_VALUES


def _is_nullish(raw: Any) -> bool:
    """Return True if a scalar value is None / NaN / NaT."""
    if raw is None:
        return True
    try:
        return bool(pd.isna(raw))
    except (TypeError, ValueError):
        return False


def parse_time_field(raw: object) -> time | None:
    """Parse a raw AIMS time value into a ``datetime.time`` or ``None``.

    Returns ``None`` for null / placeholder values.  Unparseable values also
    return ``None`` — callers should check for warnings separately.
    """
    if _is_nullish(raw):
        return None

    s = str(raw).strip().upper()

    if s in NULL_TIME_VALUES:
        return None

    # Strip next-day markers
    s = s.replace("+1", "").replace("+2", "").strip()

    # Handle 2400 as midnight
    if s == "2400":
        return time(0, 0)

    # If no colon, try to insert one (HHMM -> HH:MM)
    if ":" not in s:
        s = s.zfill(4)
        s = f"{s[:2]}:{s[2:]}"

    try:
        return datetime.strptime(s, "%H:%M").time()
    except ValueError:
        return None


def parse_time_with_warning(raw: object) -> tuple[time | None, str | None]:
    """Parse a time field and return a warning string if unparseable.

    Returns
    -------
    (parsed_time, warning)
        ``warning`` is ``None`` when parsing succeeds or the value is a
        recognized null/placeholder.
    """
    if _is_nullish(raw):
        return None, None

    s_check = str(raw).strip().upper()
    if s_check in NULL_TIME_VALUES:
        return None, None

    result = parse_time_field(raw)
    if result is None:
        return None, f"TIME_PARSE_FAILED: could not parse '{raw}'"

    return result, None
