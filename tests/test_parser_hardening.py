"""Edge-case tests for AIMS DayRepReport parser hardening (Sprint 4).

These tests target real-world parser quirks observed in production AIMS
exports, prior to receiving real fixtures from the user. Once real
fixtures arrive, additional regression tests can be added alongside
these without changing parser behaviour.
"""

from __future__ import annotations

from datetime import time

from openpyxl import Workbook

from src.parser.dayrep_parser import (
    _norm_header,
    normalize_reg,
    parse_dayrep_report,
)
from src.parser.time_parser import parse_time_field

# ---------------------------------------------------------------------------
# normalize_reg
# ---------------------------------------------------------------------------


def test_normalize_reg_handles_space_separator() -> None:
    assert normalize_reg("VN A517") == "VN-A517"


def test_normalize_reg_handles_slash_separator() -> None:
    assert normalize_reg("VN/A517") == "VN-A517"


def test_normalize_reg_handles_no_dash() -> None:
    assert normalize_reg("VNA517") == "VN-A517"


def test_normalize_reg_collapses_double_dashes() -> None:
    assert normalize_reg("VN--A517") == "VN-A517"


def test_normalize_reg_lowercase_input() -> None:
    assert normalize_reg("vna517") == "VN-A517"


def test_normalize_reg_passes_through_canonical() -> None:
    assert normalize_reg("VN-A517") == "VN-A517"


def test_normalize_reg_returns_none_for_empty() -> None:
    assert normalize_reg("") is None
    assert normalize_reg(None) is None


# ---------------------------------------------------------------------------
# parse_time_field — Excel fractional day, datetime objects, +1 markers
# ---------------------------------------------------------------------------


def test_parse_time_field_excel_fractional_day() -> None:
    # 14:00 == 0.5833... of the day
    assert parse_time_field(0.5833333333333334) == time(14, 0)


def test_parse_time_field_excel_fractional_midnight() -> None:
    assert parse_time_field(0.0) == time(0, 0)


def test_parse_time_field_handles_plus_one_marker_with_space() -> None:
    assert parse_time_field("08:30 +1") == time(8, 30)


def test_parse_time_field_handles_plus_two_marker() -> None:
    assert parse_time_field("06:15+2") == time(6, 15)


def test_parse_time_field_strips_dot_zero_suffix() -> None:
    """`pd.read_excel` may surface integer cells as floats like 1435.0."""
    assert parse_time_field("1435.0") == time(14, 35)


def test_parse_time_field_native_time_object() -> None:
    assert parse_time_field(time(7, 45)) == time(7, 45)


# ---------------------------------------------------------------------------
# Header detection — Vietnamese accented + decomposed forms
# ---------------------------------------------------------------------------


def test_norm_header_matches_decomposed_vietnamese() -> None:
    composed = "NG\u00c0Y"  # NFC: Ngày
    decomposed = "NGA\u0300Y"  # NFD: N + g + a + combining grave + y
    assert _norm_header(composed) == _norm_header(decomposed) == "NG\u00c0Y"


def test_norm_header_uppercases_and_strips() -> None:
    assert _norm_header(" ngày bay ") == "NG\u00c0Y BAY"


def _build_vietnamese_dayrep(path: str) -> None:
    """Create a minimal Vietnamese-header DayRepReport for parser testing."""
    wb = Workbook()
    ws = wb.active
    assert ws is not None
    ws.append(["Báo cáo ngày 24/04/2026"])  # title row
    ws.append([])
    ws.append(
        [
            "Ngày",
            "Chuyến bay",
            "Đăng ký",
            "Loại tàu",
            "Đi",
            "Đến",
            "Giờ KH đi",
            "Giờ KH đến",
        ]
    )
    ws.append(
        [
            "24/04/2026",
            "VN101",
            "VN-A517",
            "A321",
            "HAN",
            "SGN",
            "14:30",
            "16:30",
        ]
    )
    ws.append(
        [
            "24/04/2026",
            "VN102",
            "VN-A518",
            "A350",
            "SGN",
            "HAN",
            "10:00",
            "12:00",
        ]
    )
    wb.save(path)


def test_parse_dayrep_with_vietnamese_headers(tmp_path) -> None:
    """Vietnamese-header export must produce a canonical-column DataFrame."""
    f = tmp_path / "vi_dayrep.xlsx"
    _build_vietnamese_dayrep(str(f))
    df, warnings = parse_dayrep_report(str(f))
    assert not df.empty, f"expected rows, got warnings: {warnings}"
    assert {"flight_no", "aircraft_reg", "origin", "destination", "std", "sta"} <= set(df.columns)
    assert sorted(df["flight_no"].tolist()) == ["VN101", "VN102"]
    assert df.loc[df["flight_no"] == "VN101", "std"].iloc[0] == time(14, 30)


def test_parse_dayrep_with_normalized_reg(tmp_path) -> None:
    """REG variants (no dash, slash, space) all normalise to canonical form."""
    wb = Workbook()
    ws = wb.active
    assert ws is not None
    ws.append(["Date", "Flt", "Reg", "AC", "Dep", "Arr", "STD", "STA"])
    ws.append(["24/04/2026", "VN101", "VNA517", "A321", "HAN", "SGN", "14:30", "16:30"])
    ws.append(["24/04/2026", "VN102", "VN/A518", "A321", "HAN", "SGN", "07:00", "09:00"])
    ws.append(["24/04/2026", "VN103", "VN A519", "A321", "HAN", "SGN", "08:00", "10:00"])
    f = tmp_path / "reg_variants.xlsx"
    wb.save(str(f))
    df, _warnings = parse_dayrep_report(str(f))
    regs = sorted(df["aircraft_reg"].dropna().tolist())
    assert regs == ["VN-A517", "VN-A518", "VN-A519"]
