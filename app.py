"""OCC IROPS Recovery Dashboard — Streamlit UI.

An automated AIMS report reader that reads the AIMS DayRepReport,
calculates the impact structure, and prepares a review list for OCC.
"""

from __future__ import annotations

import tempfile
from datetime import date, time

import streamlit as st

from src.cascade.cascade_detector import compute_kpis, detect_cascade
from src.config import MVP_LIMITATION_WARNING
from src.export.excel_exporter import export_to_excel
from src.models.event import AirportClosureEvent
from src.parser.dayrep_parser import parse_dayrep_report

st.set_page_config(page_title="OCC IROPS Recovery Dashboard", layout="wide")

# ─── Sidebar ────────────────────────────────────────────────────────────
st.sidebar.title("OCC IROPS Recovery Dashboard")
st.sidebar.markdown("---")

uploaded_file = st.sidebar.file_uploader(
    "Upload DayRepReport (Excel)", type=["xlsx", "xls"]
)

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
with tempfile.NamedTemporaryFile(suffix=".xlsx", delete=False) as tmp:
    tmp.write(uploaded_file.getvalue())
    tmp_path = tmp.name

with st.spinner("Parsing DayRepReport..."):
    df, parse_warnings = parse_dayrep_report(tmp_path)

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

# ─── Affected Flights Table ─────────────────────────────────────────────
st.subheader("Affected Flights")

affected = df_result[df_result["impact_level_numeric"].notna()].copy()

if affected.empty:
    st.info("No flights affected by the specified closure event.")
else:
    display_cols = [
        "flight_no", "aircraft_reg", "aircraft_type",
        "origin", "destination", "std", "sta",
        "impact_level_display", "impact_reason",
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
            ac_flights = df_result[df_result["aircraft_reg"] == reg].sort_values("std", na_position="last")
            rotation_cols = [
                "flight_no", "origin", "destination", "std", "sta",
                "impact_level_display", "impact_reason",
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
