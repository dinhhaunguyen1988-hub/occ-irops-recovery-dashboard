"""Excel report exporter for OCC IROPS Recovery Dashboard."""

from __future__ import annotations

from datetime import time
from io import BytesIO

import pandas as pd

from src.models.event import AirportClosureEvent


def _format_time(t: time | None) -> str:
    """Format a time object to HH:MM string."""
    if t is None:
        return ""
    return t.strftime("%H:%M")


def export_to_excel(
    df: pd.DataFrame,
    event: AirportClosureEvent,
    kpis: dict,
    warnings: list[str],
) -> BytesIO:
    """Export analysis results to an Excel workbook in memory.

    Sheets:
    - Parameters: closure event details
    - KPI Summary: high-level metrics
    - Affected Flights: full affected-flight table
    - All Flights: complete dataset with impact levels
    - Data Quality Warnings: list of parser warnings

    Returns a BytesIO buffer containing the .xlsx file.
    """
    output = BytesIO()

    with pd.ExcelWriter(output, engine="xlsxwriter") as writer:
        # --- Parameters sheet ---
        params_data = {
            "Parameter": [
                "Airport",
                "Closure Date",
                "Closure Start",
                "Closure End",
                "Boundary Rule",
            ],
            "Value": [
                event.airport,
                str(event.closure_date),
                event.start_time.strftime("%H:%M"),
                event.end_time.strftime("%H:%M"),
                "Start inclusive, End exclusive",
            ],
        }
        pd.DataFrame(params_data).to_excel(writer, sheet_name="Parameters", index=False)

        # --- KPI Summary sheet ---
        kpi_data = {
            "KPI": list(kpis.keys()),
            "Value": list(kpis.values()),
        }
        pd.DataFrame(kpi_data).to_excel(writer, sheet_name="KPI Summary", index=False)

        # --- Affected Flights sheet ---
        affected = df[df["impact_level_numeric"].notna()].copy()
        display_cols = [
            "flight_no",
            "aircraft_reg",
            "aircraft_type",
            "origin",
            "destination",
            "std",
            "sta",
            "impact_level_display",
            "impact_reason",
            "impact_explanation",
            "cascade_root_flight",
            "data_quality_warning",
        ]
        existing_display_cols = [c for c in display_cols if c in affected.columns]
        affected_display = affected[existing_display_cols].copy()

        for tc in ["std", "sta"]:
            if tc in affected_display.columns:
                affected_display[tc] = affected_display[tc].apply(_format_time)

        affected_display.to_excel(writer, sheet_name="Affected Flights", index=False)

        # --- All Flights sheet ---
        all_display = df.copy()
        for tc in ["std", "sta"]:
            if tc in all_display.columns:
                all_display[tc] = all_display[tc].apply(_format_time)
        all_display.to_excel(writer, sheet_name="All Flights", index=False)

        # --- Data Quality Warnings sheet ---
        if warnings:
            warn_df = pd.DataFrame({"Warning": warnings})
        else:
            warn_df = pd.DataFrame({"Warning": ["No warnings"]})
        warn_df.to_excel(writer, sheet_name="Data Quality Warnings", index=False)

    output.seek(0)
    return output
