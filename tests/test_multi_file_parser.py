"""Tests for the multi-file parser helper."""

import os
import tempfile

import pandas as pd

from src.parser.multi_file import parse_multiple_dayrep_reports


def _write_dayrep(rows: list[dict]) -> str:
    """Write a synthetic DayRepReport-style sheet to a temp xlsx and return its path."""
    headers = ["DATE", "FLT", "REG", "AC", "DEP", "ARR", "STD", "STA"]
    data = [headers] + [
        [
            r.get("date", ""),
            r.get("flt", ""),
            r.get("reg", ""),
            r.get("ac", ""),
            r.get("dep", ""),
            r.get("arr", ""),
            r.get("std", ""),
            r.get("sta", ""),
        ]
        for r in rows
    ]
    df = pd.DataFrame(data)
    fd, path = tempfile.mkstemp(suffix=".xlsx")
    os.close(fd)
    df.to_excel(path, header=False, index=False)
    return path


def test_concatenates_two_files():
    f1 = _write_dayrep(
        [
            {
                "date": "24/04/2026",
                "flt": "VN101",
                "reg": "VN-A500",
                "ac": "A321",
                "dep": "SGN",
                "arr": "HAN",
                "std": "13:00",
                "sta": "15:00",
            },
        ]
    )
    f2 = _write_dayrep(
        [
            {
                "date": "25/04/2026",
                "flt": "VN102",
                "reg": "VN-A500",
                "ac": "A321",
                "dep": "HAN",
                "arr": "SGN",
                "std": "07:00",
                "sta": "08:30",
            },
        ]
    )

    df, warnings = parse_multiple_dayrep_reports([f1, f2])

    assert len(df) == 2
    assert set(df["flight_no"]) == {"VN101", "VN102"}
    assert "source_file_index" in df.columns
    assert set(df["source_file_index"]) == {1, 2}


def test_returns_empty_when_all_files_unparseable():
    fd, bad_path = tempfile.mkstemp(suffix=".xlsx")
    os.close(fd)
    pd.DataFrame([["random", "garbage"]]).to_excel(bad_path, header=False, index=False)

    df, warnings = parse_multiple_dayrep_reports([bad_path])

    assert df.empty
    # Warning is prefixed with file index
    assert any(w.startswith("file#1:") for w in warnings)
