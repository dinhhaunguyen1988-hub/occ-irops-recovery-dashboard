"""AIMS DayRepReport parser.

Loads a DayRepReport Excel file, detects header row dynamically,
maps columns to canonical schema, normalizes data, removes footer rows,
and returns a clean DataFrame with data quality warnings.
"""

from __future__ import annotations

import re
from datetime import datetime
from typing import Optional

import pandas as pd

from src.config import (
    FLIGHT_NO_PATTERN,
    HEADER_KEYWORD_MAP,
    MIN_HEADER_MATCH,
    REG_PATTERN,
)
from src.parser.time_parser import parse_time_with_warning


# ---------------------------------------------------------------------------
# Aircraft registration normalization
# ---------------------------------------------------------------------------

def normalize_reg(raw: object) -> Optional[str]:
    """Normalize an aircraft registration string.

    - Strips whitespace
    - Uppercases
    - Inserts hyphen for VN registrations missing it (e.g. VNA500 -> VN-A500)
    """
    if raw is None or pd.isna(raw):
        return None

    s = str(raw).strip().upper()

    if not s:
        return None

    # Convert VNA500 -> VN-A500
    if re.match(r"^VN[A-Z0-9]{3,5}$", s) and "-" not in s:
        s = "VN-" + s[2:]

    return s


# ---------------------------------------------------------------------------
# Header detection
# ---------------------------------------------------------------------------

def find_header_row(df_raw: pd.DataFrame) -> int:
    """Find the header row index by keyword matching.

    The first row that matches at least ``MIN_HEADER_MATCH`` of the 8
    canonical keyword groups is returned.

    Raises ``ValueError`` if no header row is found.
    """
    for i, row in df_raw.iterrows():
        row_upper = [str(v).strip().upper() for v in row]
        matched = sum(
            1
            for aliases in HEADER_KEYWORD_MAP.values()
            if any(alias in row_upper for alias in aliases)
        )
        if matched >= MIN_HEADER_MATCH:
            return int(i)

    raise ValueError("HEADER_NOT_FOUND: Cannot detect header row in DayRepReport")


def _map_column(col_name: str) -> Optional[str]:
    """Map a raw column name to its canonical name using keyword aliases."""
    col_upper = col_name.strip().upper()
    canonical_map = {
        "DATE": "flight_date",
        "FLT": "flight_no",
        "REG": "aircraft_reg",
        "AC": "aircraft_type",
        "DEP": "origin",
        "ARR": "destination",
        "STD": "std",
        "STA": "sta",
    }
    for group_key, aliases in HEADER_KEYWORD_MAP.items():
        if col_upper in aliases:
            return canonical_map[group_key]
    return None


# ---------------------------------------------------------------------------
# Footer / invalid row filtering
# ---------------------------------------------------------------------------

def _is_valid_flight_row(row: pd.Series) -> bool:
    """Return True if the row looks like a valid flight record."""
    flt = str(row.get("flight_no", "")).strip()
    date_val = str(row.get("flight_date", "")).strip()

    if not flt or not date_val:
        return False

    # Flight number should match pattern
    if not re.match(FLIGHT_NO_PATTERN, flt):
        return False

    return True


# ---------------------------------------------------------------------------
# Main parser
# ---------------------------------------------------------------------------

def parse_dayrep_report(
    file_path: str,
    sheet_name: int | str = 0,
) -> tuple[pd.DataFrame, list[str]]:
    """Parse an AIMS DayRepReport Excel file.

    Parameters
    ----------
    file_path : str
        Path to the Excel file.
    sheet_name : int | str
        Sheet index or name (default: first sheet).

    Returns
    -------
    (df, warnings)
        ``df`` is a DataFrame with canonical columns.
        ``warnings`` is a list of data-quality warning strings.
    """
    warnings: list[str] = []

    # 1. Load raw Excel (no header assumption)
    df_raw = pd.read_excel(file_path, sheet_name=sheet_name, header=None)

    # 2. Detect header row
    try:
        header_idx = find_header_row(df_raw)
    except ValueError as exc:
        warnings.append(str(exc))
        return pd.DataFrame(), warnings

    # 3. Extract header names and data rows
    raw_headers = [str(v).strip() for v in df_raw.iloc[header_idx]]
    df_data = df_raw.iloc[header_idx + 1:].copy()
    df_data.columns = raw_headers
    df_data = df_data.reset_index(drop=True)

    # 4. Map columns to canonical names
    rename_map: dict[str, str] = {}
    for col in df_data.columns:
        canonical = _map_column(col)
        if canonical is not None:
            rename_map[col] = canonical

    df_data = df_data.rename(columns=rename_map)

    # Keep only canonical columns that exist
    canonical_cols = [
        "flight_date", "flight_no", "aircraft_reg", "aircraft_type",
        "origin", "destination", "std", "sta",
    ]
    existing_cols = [c for c in canonical_cols if c in df_data.columns]
    df_data = df_data[existing_cols].copy()

    # Store original row number (relative to Excel, 1-based, accounting for header offset)
    df_data["raw_row_number"] = range(header_idx + 2, header_idx + 2 + len(df_data))

    # 5. Basic cleanup — convert everything to string for uniform processing
    for col in ["flight_no", "aircraft_reg", "aircraft_type", "origin", "destination"]:
        if col in df_data.columns:
            df_data[col] = df_data[col].astype(str).str.strip()

    # 6. Normalize aircraft registration
    if "aircraft_reg" in df_data.columns:
        df_data["aircraft_reg"] = df_data["aircraft_reg"].apply(normalize_reg)
        invalid_reg_mask = df_data["aircraft_reg"].notna() & ~df_data["aircraft_reg"].str.match(
            REG_PATTERN, na=False
        )
        for idx in df_data[invalid_reg_mask].index:
            warnings.append(
                f"REG_INVALID: row {df_data.at[idx, 'raw_row_number']}, "
                f"reg='{df_data.at[idx, 'aircraft_reg']}'"
            )

    # 7. Parse time fields
    df_data["data_quality_warning"] = None

    for time_col in ["std", "sta"]:
        if time_col not in df_data.columns:
            continue
        parsed_times = []
        for idx, raw_val in df_data[time_col].items():
            t, warn = parse_time_with_warning(raw_val)
            parsed_times.append(t)
            if warn:
                warnings.append(
                    f"{warn} at row {df_data.at[idx, 'raw_row_number']} col {time_col}"
                )
                existing_warn = df_data.at[idx, "data_quality_warning"]
                if existing_warn:
                    df_data.at[idx, "data_quality_warning"] = f"{existing_warn}; {warn}"
                else:
                    df_data.at[idx, "data_quality_warning"] = warn
        df_data[time_col] = parsed_times

    # 8. Parse flight date
    if "flight_date" in df_data.columns:
        parsed_dates = []
        for idx, raw_val in df_data["flight_date"].items():
            if pd.isna(raw_val) or str(raw_val).strip() == "" or str(raw_val).strip().lower() == "nan":
                parsed_dates.append(None)
                continue
            raw_str = str(raw_val).strip()
            parsed_date = None
            for fmt in ("%d/%m/%Y", "%Y-%m-%d", "%d-%m-%Y", "%m/%d/%Y", "%d.%m.%Y"):
                try:
                    parsed_date = datetime.strptime(raw_str, fmt).date()
                    break
                except ValueError:
                    continue
            if parsed_date is None:
                try:
                    parsed_date = pd.to_datetime(raw_val).date()
                except Exception:
                    warnings.append(
                        f"DATE_PARSE_FAILED: row {df_data.at[idx, 'raw_row_number']}, "
                        f"value='{raw_val}'"
                    )
            parsed_dates.append(parsed_date)
        df_data["flight_date"] = parsed_dates

    # 9. Remove footer / non-flight rows
    valid_mask = df_data.apply(_is_valid_flight_row, axis=1)
    skipped_count = (~valid_mask).sum()
    if skipped_count > 0:
        for idx in df_data[~valid_mask].index:
            warnings.append(
                f"FOOTER_ROW_SKIPPED: row {df_data.at[idx, 'raw_row_number']}"
            )
    df_data = df_data[valid_mask].reset_index(drop=True)

    return df_data, warnings
