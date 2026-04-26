"""OCC IROPS Recovery Dashboard — Streamlit UI.

An automated AIMS report reader that reads the AIMS DayRepReport,
calculates the impact structure, and prepares a review list for OCC.
"""

from __future__ import annotations

import hashlib
import tempfile
from datetime import date, time

import pandas as pd
import streamlit as st

from src.cascade.cascade_detector import compute_kpis, detect_cascade
from src.config import MVP_LIMITATION_WARNING
from src.export.excel_exporter import export_to_excel
from src.logging_config import get_logger, setup_logging
from src.models.event import AirportClosureEvent
from src.parser.dayrep_parser import parse_dayrep_report

setup_logging()
logger = get_logger(__name__)

st.set_page_config(page_title="OCC IROPS Recovery Dashboard", layout="wide")

# ─── Sidebar ────────────────────────────────────────────────────────────
st.sidebar.title("OCC IROPS Recovery Dashboard")
st.sidebar.markdown("---")

uploaded_file = st.sidebar.file_uploader("Upload DayRepReport (Excel)", type=["xlsx", "xls"])

airport_code = st.sidebar.text_input("Airport Code", value="HAN")
closure_date = st.sidebar.date_input("Closure Date", value=date(2026, 4, 24))
closure_start = st.sidebar.time_input("Closure Start Time", value=time(14, 0))
closure_end = st.sidebar.time_input("Closure End Time", value=time(18, 0))

run_analysis = st.sidebar.button("Run Analysis", type="primary")

# ─── Main area ──────────────────────────────────────────────────────────
st.title("OCC IROPS Recovery Dashboard")

st.warning(MVP_LIMITATION_WARNING)

if not uploaded_file:
    st.info("Upload a DayRepReport file in the sidebar to begin analysis.")
    st.stop()

if not run_analysis:
    st.info("Configure parameters in the sidebar and click **Run Analysis**.")
    st.stop()

# ─── Validate event ────────────────────────────────────────────────────
try:
    event = AirportClosureEvent(
        airport=airport_code,
        closure_date=closure_date,
        start_time=closure_start,
        end_time=closure_end,
    )
except ValueError as e:
    st.error(str(e))
    st.stop()

# ─── Parse file ─────────────────────────────────────────────────────────
file_bytes = uploaded_file.getvalue()
file_hash = hashlib.sha256(file_bytes).hexdigest()[:12]
logger.info(
    "upload_received",
    extra={
        "filename": uploaded_file.name,
        "size_bytes": len(file_bytes),
        "file_hash": file_hash,
        "event": str(event),
    },
)

with tempfile.NamedTemporaryFile(suffix=".xlsx", delete=False) as tmp:
    tmp.write(file_bytes)
    tmp_path = tmp.name

with st.spinner("Parsing DayRepReport..."):
    df, parse_warnings = parse_dayrep_report(tmp_path)

logger.info(
    "parse_completed",
    extra={
        "file_hash": file_hash,
        "rows_parsed": int(len(df)),
        "warnings_count": len(parse_warnings),
    },
)

if df.empty:
    st.error("Could not parse the uploaded file. Check warnings below.")
    if parse_warnings:
        st.subheader("Data Quality Warnings")
        for w in parse_warnings:
            st.warning(w)
    st.stop()

# ─── Run cascade detection ──────────────────────────────────────────────
with st.spinner("Running cascade detection..."):
    df_result = detect_cascade(df, event)
    kpis = compute_kpis(df_result)

affected = df_result[df_result["impact_level_numeric"].notna()].copy()

logger.info(
    "cascade_completed",
    extra={
        "file_hash": file_hash,
        "event": str(event),
        **{f"kpi_{k}": v for k, v in kpis.items()},
    },
)

# ─── Data Quality Warnings ─────────────────────────────────────────────
if parse_warnings:
    with st.expander(f"Data Quality Warnings ({len(parse_warnings)})", expanded=False):
        for w in parse_warnings:
            st.warning(w)

# ─── KPI Cards ──────────────────────────────────────────────────────────
st.subheader("Summary KPIs")
st.caption(f"Event: {event}")

col1, col2, col3, col4, col5 = st.columns(5)
col1.metric("Total Flights", kpis["total_flights"])
col2.metric("Affected Flights", kpis["affected_flights"])
col3.metric("Level 1", kpis["level_1_count"])
col4.metric("Level 2", kpis["level_2_count"])
col5.metric("Level 3+", kpis["level_3plus_count"])

st.metric("Aircraft Affected", kpis["aircraft_affected"])

# ─── Impact Distribution Chart ──────────────────────────────────────────
st.subheader("Impact Analysis")

chart_col1, chart_col2 = st.columns(2)

with chart_col1:
    st.markdown("**Impact Level Distribution**")
    impact_data = pd.DataFrame(
        {
            "Impact Level": ["Level 1", "Level 2", "Level 3+", "Not Affected"],
            "Count": [
                kpis["level_1_count"],
                kpis["level_2_count"],
                kpis["level_3plus_count"],
                kpis["total_flights"] - kpis["affected_flights"],
            ],
        }
    )
    impact_data = impact_data[impact_data["Count"] > 0]
    st.bar_chart(impact_data.set_index("Impact Level"))

with chart_col2:
    st.markdown("**Affected vs Unaffected Flights**")
    pie_data = pd.DataFrame(
        {
            "Category": ["Affected", "Not Affected"],
            "Count": [
                kpis["affected_flights"],
                kpis["total_flights"] - kpis["affected_flights"],
            ],
        }
    )
    st.bar_chart(pie_data.set_index("Category"))

# ─── Flight Timeline ───────────────────────────────────────────────────
if not affected.empty:
    st.markdown("**Affected Flights Timeline**")
    timeline_df = affected.copy()
    timeline_df = timeline_df[timeline_df["std"].notna()].copy()
    if not timeline_df.empty:
        timeline_df["hour"] = timeline_df["std"].apply(lambda t: t.hour if t is not None else None)
        timeline_df = timeline_df[timeline_df["hour"].notna()]
        hour_counts = (
            timeline_df.groupby(["hour", "impact_level_display"]).size().reset_index(name="count")
        )
        pivot = hour_counts.pivot(
            index="hour", columns="impact_level_display", values="count"
        ).fillna(0)
        st.bar_chart(pivot)
        st.caption(
            f"Closure window: {event.start_time.strftime('%H:%M')}–"
            f"{event.end_time.strftime('%H:%M')} "
            f"(shaded area represents closure period)"
        )

# ─── Affected Flights Table ─────────────────────────────────────────────
st.subheader("Affected Flights")

if affected.empty:
    st.info("No flights affected by the specified closure event.")
else:
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
        "data_quality_warning",
    ]
    existing_cols = [c for c in display_cols if c in affected.columns]

    # Format time columns for display
    affected_display = affected[existing_cols].copy()
    for tc in ["std", "sta"]:
        if tc in affected_display.columns:
            affected_display[tc] = affected_display[tc].apply(
                lambda t: t.strftime("%H:%M") if t is not None else ""
            )

    st.dataframe(affected_display, use_container_width=True, hide_index=True)

# ─── Aircraft Rotation View ────────────────────────────────────────────
st.subheader("Aircraft Rotation View")

affected_aircraft = affected["aircraft_reg"].unique().tolist() if not affected.empty else []

if affected_aircraft:
    for reg in sorted(affected_aircraft):
        if reg is None:
            continue
        with st.expander(f"Aircraft: {reg}"):
            ac_flights = df_result[df_result["aircraft_reg"] == reg].sort_values(
                "std", na_position="last"
            )
            rotation_cols = [
                "flight_no",
                "origin",
                "destination",
                "std",
                "sta",
                "impact_level_display",
                "impact_reason",
            ]
            existing_rot_cols = [c for c in rotation_cols if c in ac_flights.columns]
            ac_display = ac_flights[existing_rot_cols].copy()
            for tc in ["std", "sta"]:
                if tc in ac_display.columns:
                    ac_display[tc] = ac_display[tc].apply(
                        lambda t: t.strftime("%H:%M") if t is not None else ""
                    )
            st.dataframe(ac_display, use_container_width=True, hide_index=True)
else:
    st.info("No affected aircraft to display.")

# ─── Export Excel ───────────────────────────────────────────────────────
st.subheader("Export")

excel_buffer = export_to_excel(df_result, event, kpis, parse_warnings)
st.download_button(
    label="Download Excel Report",
    data=excel_buffer,
    file_name=f"IROPS_Report_{event.airport}_{event.closure_date}.xlsx",
    mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
    type="primary",
)
