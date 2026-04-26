"""Tests for AIMS time field parser."""

from datetime import time

from src.parser.time_parser import parse_time_field, parse_time_with_warning


class TestParseTimeField:
    def test_standard_hhmm_colon(self):
        assert parse_time_field("14:35") == time(14, 35)

    def test_hhmm_no_colon(self):
        assert parse_time_field("1435") == time(14, 35)

    def test_single_digit_hour_colon(self):
        assert parse_time_field("6:05") == time(6, 5)

    def test_hmm_no_colon(self):
        assert parse_time_field("605") == time(6, 5)

    def test_midnight_2400(self):
        assert parse_time_field("2400") == time(0, 0)

    def test_placeholder_dashes(self):
        assert parse_time_field("--:--") is None

    def test_placeholder_double_dash(self):
        assert parse_time_field("--") is None

    def test_empty_string(self):
        assert parse_time_field("") is None

    def test_none_value(self):
        assert parse_time_field(None) is None

    def test_next_day_marker_plus1(self):
        assert parse_time_field("00:00+1") == time(0, 0)

    def test_next_day_marker_plus2(self):
        assert parse_time_field("00:00+2") == time(0, 0)

    def test_na_string(self):
        assert parse_time_field("N/A") is None

    def test_none_string(self):
        assert parse_time_field("NONE") is None

    def test_null_string(self):
        assert parse_time_field("NULL") is None

    def test_invalid_value(self):
        assert parse_time_field("abc") is None

    def test_case_insensitive(self):
        assert parse_time_field("n/a") is None

    def test_whitespace(self):
        assert parse_time_field("  14:35  ") == time(14, 35)

    def test_zero_padded(self):
        assert parse_time_field("06:05") == time(6, 5)

    def test_numeric_input(self):
        assert parse_time_field(1435) == time(14, 35)


class TestParseTimeWithWarning:
    def test_valid_time_no_warning(self):
        t, w = parse_time_with_warning("14:35")
        assert t == time(14, 35)
        assert w is None

    def test_null_no_warning(self):
        t, w = parse_time_with_warning("--:--")
        assert t is None
        assert w is None

    def test_none_no_warning(self):
        t, w = parse_time_with_warning(None)
        assert t is None
        assert w is None

    def test_invalid_returns_warning(self):
        t, w = parse_time_with_warning("abc")
        assert t is None
        assert w is not None
        assert "TIME_PARSE_FAILED" in w
