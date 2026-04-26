"""AIMS time field parser.

Handles all known AIMS DayRepReport time formats:
- HH:MM (e.g. 14:35)
- HHMM  (e.g. 1435)
- H:MM  (e.g. 6:05)
- HMM   (e.g. 605)
- 2400  (midnight, mapped to 00:00)
- Blank / null / placeholder
- Next-day markers (+1, +2)
- Excel time-as-fractional-day (e.g. 0.5833 → 14:00) when sheet stores time as a real number
- Python ``datetime.time`` / ``datetime.datetime`` cells (when openpyxl preserves type)
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

    # Native ``datetime`` / ``time`` objects (some Excel cells preserve type).
    if isinstance(raw, datetime):
        return raw.time()
    if isinstance(raw, time):
        return raw

    # Excel time-as-fractional-day. ``raw`` is a float in [0, 1) where 0.5 == 12:00.
    # We accept ints in that range too (rare but possible).
    if isinstance(raw, (int, float)) and not isinstance(raw, bool):
        f = float(raw)
        if 0.0 <= f < 1.0:
            total_minutes = int(round(f * 24 * 60))
            hh, mm = divmod(total_minutes, 60)
            if hh == 24:
                return time(0, 0)
            return time(hh, mm)
        # Fall through to string handling for plain integer HHMM values

    s = str(raw).strip().upper()

    if s in NULL_TIME_VALUES:
        return None

    # Strip next-day markers (also tolerate spaces, e.g. "08:30 +1")
    for marker in ("+1", "+2", "+3"):
        s = s.replace(marker, "")
    s = s.strip()

    # Handle 2400 as midnight
    if s == "2400":
        return time(0, 0)

    # If no colon, try to insert one (HHMM -> HH:MM). Drop trailing ``.0`` that
    # ``pd.read_excel`` introduces for numeric cells ("1435.0" → "1435").
    if ":" not in s:
        if s.endswith(".0"):
            s = s[:-2]
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
