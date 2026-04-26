"""Helpers for combining multiple DayRepReport files into a single canonical
DataFrame so cascade detection can span overnight rotations.
"""

from __future__ import annotations

import pandas as pd

from src.parser.dayrep_parser import parse_dayrep_report


def parse_multiple_dayrep_reports(
    file_paths: list[str],
) -> tuple[pd.DataFrame, list[str]]:
    """Parse one or more DayRepReport files and concatenate the results.

    Each warning is prefixed with the source file index so callers can
    correlate it back to the original file. Returns an empty DataFrame +
    accumulated warnings if every file fails to parse.
    """
    frames: list[pd.DataFrame] = []
    warnings: list[str] = []

    for i, path in enumerate(file_paths, start=1):
        df, warns = parse_dayrep_report(path)
        if df.empty and not warns:
            continue
        for w in warns:
            warnings.append(f"file#{i}: {w}")
        if not df.empty:
            df = df.copy()
            df["source_file_index"] = i
            frames.append(df)

    if not frames:
        return pd.DataFrame(), warnings

    combined = pd.concat(frames, ignore_index=True)
    return combined, warnings
