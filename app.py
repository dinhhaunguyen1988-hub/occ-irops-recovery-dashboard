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
from src.cascade.ranking import compute_priority
from src.config import MVP_LIMITATION_WARNING
from src.export.excel_exporter import export_to_excel
from src.logging_config import get_logger, setup_logging
from src.models.event import AirportClosureEvent
from src.parser.multi_file import parse_multiple_dayrep_reports
from src.visualization.gantt import build_rotation_gantt

setup_logging()
logger = get_logger(__name__)

st.set_page_config(page_title="OCC IROPS Recovery Dashboard", layout="wide")

# ─── Sidebar ────────────────────────────────────────────────────────────
st.sidebar.title("OCC IROPS Recovery Dashboard")
st.sidebar.markdown("---")

uploaded_files = st.sidebar.file_uploader(
    "Upload DayRepReport(s) (Excel)",
    type=["xlsx", "xls"],
    accept_multiple_files=True,
    help="Upload the closure-day file plus the next-day file to capture overnight cascade.",
)

airport_code = st.sidebar.text_input("Airport Code", value="HAN")
closure_date = st.sidebar.date_input("Closure Date", value=date(2026, 4, 24))
closure_start = st.sidebar.time_input("Closure Start Time", value=time(14, 0))
closure_end = st.sidebar.time_input("Closure End Time", value=time(18, 0))

st.sidebar.markdown("---")
whatif_enabled = st.sidebar.checkbox(
    "What-if mode",
    value=False,
    help="Compare the baseline closure window with an alternative one.",
)
whatif_start = closure_start
whatif_end = closure_end
if whatif_enabled:
    whatif_start = st.sidebar.time_input("What-if Start Time", value=closure_start, key="wi_start")
    whatif_end = st.sidebar.time_input("What-if End Time", value=closure_end, key="wi_end")

run_analysis = st.sidebar.button("Run Analysis", type="primary")

# ─── Main area ──────────────────────────────────────────────────────────
st.title("OCC IROPS Recovery Dashboard")

st.warning(MVP_LIMITATION_WARNING)

if not uploaded_files:
    st.info("Upload one or more DayRepReport files in the sidebar to begin analysis.")
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

whatif_event: AirportClosureEvent | None = None
if whatif_enabled:
    try:
        whatif_event = AirportClosureEvent(
            airport=airport_code,
            closure_date=closure_date,
            start_time=whatif_start,
            end_time=whatif_end,
        )
    except ValueError as e:
        st.error(f"What-if: {e}")
        st.stop()

# ─── Parse files ────────────────────────────────────────────────────────
tmp_paths: list[str] = []
total_bytes = 0
file_hashes: list[str] = []
for f in uploaded_files:
    raw = f.getvalue()
    total_bytes += len(raw)
    file_hashes.append(hashlib.sha256(raw).hexdigest()[:12])
    with tempfile.NamedTemporaryFile(suffix=".xlsx", delete=False) as tmp:
        tmp.write(raw)
        tmp_paths.append(tmp.name)

logger.info(
    "upload_received",
    extra={
        "filenames": [f.name for f in uploaded_files],
        "size_bytes": total_bytes,
        "file_hashes": file_hashes,
        "event": str(event),
        "whatif": bool(whatif_enabled),
    },
)

with st.spinner(f"Parsing {len(tmp_paths)} DayRepReport file(s)..."):
    df, parse_warnings = parse_multiple_dayrep_reports(tmp_paths)

logger.info(
    "parse_completed",
    extra={
        "file_hashes": file_hashes,
        "rows_parsed": int(len(df)),
        "warnings_count": len(parse_warnings),
    },
)

if df.empty:
    st.error("Could not parse the uploaded file(s). Check warnings below.")
    if parse_warnings:
        st.subheader("Data Quality Warnings")
        for w in parse_warnings:
            st.warning(w)
    st.stop()

# ─── Run cascade detection ──────────────────────────────────────────────
with st.spinner("Running cascade detection..."):
    df_result = detect_cascade(df, event)
    df_result = compute_priority(df_result)
    kpis = compute_kpis(df_result)

affected = df_result[df_result["impact_level_numeric"].notna()].copy()

logger.info(
    "cascade_completed",
    extra={
        "file_hashes": file_hashes,
        "event": str(event),
        **{f"kpi_{k}": v for k, v in kpis.items()},
    },
)

# ─── What-if comparison ────────────────────────────────────────────────
whatif_diff: dict[str, set[str]] = {}
if whatif_event is not None:
    df_whatif = detect_cascade(df, whatif_event)
    affected_baseline = set(
        df_result[df_result["impact_level_numeric"].notna()]["flight_no"].astype(str)
    )
    affected_whatif = set(
        df_whatif[df_whatif["impact_level_numeric"].notna()]["flight_no"].astype(str)
    )
    whatif_diff = {
        "added": affected_whatif - affected_baseline,
        "removed": affected_baseline - affected_whatif,
        "unchanged": affected_baseline & affected_whatif,
    }
    logger.info(
        "whatif_completed",
        extra={
            "whatif_event": str(whatif_event),
            "added_count": len(whatif_diff["added"]),
            "removed_count": len(whatif_diff["removed"]),
            "unchanged_count": len(whatif_diff["unchanged"]),
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
if len(uploaded_files) > 1:
    st.caption(f"Multi-file run: {len(uploaded_files)} files merged for overnight cascade.")

col1, col2, col3, col4, col5 = st.columns(5)
col1.metric("Total Flights", kpis["total_flights"])
col2.metric("Affected Flights", kpis["affected_flights"])
col3.metric("Level 1", kpis["level_1_count"])
col4.metric("Level 2", kpis["level_2_count"])
col5.metric("Level 3+", kpis["level_3plus_count"])

st.metric("Aircraft Affected", kpis["aircraft_affected"])

# ─── What-if diff panel ────────────────────────────────────────────────
if whatif_event is not None:
    st.subheader("What-if Comparison")
    st.caption(f"Baseline: {event}")
    st.caption(f"What-if : {whatif_event}")

    diff_col1, diff_col2, diff_col3 = st.columns(3)
    diff_col1.metric("Newly Affected", len(whatif_diff["added"]))
    diff_col2.metric("No Longer Affected", len(whatif_diff["removed"]))
    diff_col3.metric("Unchanged", len(whatif_diff["unchanged"]))

    if whatif_diff["added"]:
        st.markdown("**Newly affected flights** (in what-if but not in baseline):")
        st.write(", ".join(sorted(whatif_diff["added"])))
    if whatif_diff["removed"]:
        st.markdown("**No longer affected** (in baseline but not in what-if):")
        st.write(", ".join(sorted(whatif_diff["removed"])))

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

# ─── Aircraft Rotation Gantt ───────────────────────────────────────────
st.subheader("Aircraft Rotation Gantt")
if affected.empty:
    st.info("No affected aircraft to plot.")
else:
    affected_regs = set(affected["aircraft_reg"].dropna().astype(str).tolist())
    rotation_df = df_result[df_result["aircraft_reg"].astype(str).isin(affected_regs)].copy()
    fig = build_rotation_gantt(rotation_df, event)
    if fig is None:
        st.info("Plotly is not available; install `plotly` to enable the Gantt view.")
    else:
        st.plotly_chart(fig, use_container_width=True)

# ─── Affected Flights Table (priority-ranked) ──────────────────────────
st.subheader("Affected Flights (priority-ranked)")

if affected.empty:
    st.info("No flights affected by the specified closure event.")
else:
    affected_ranked = affected.sort_values(
        ["priority_score", "impact_level_numeric"],
        ascending=[False, True],
    )
    display_cols = [
        "flight_no",
        "aircraft_reg",
        "aircraft_type",
        "origin",
        "destination",
        "flight_date",
        "std",
        "sta",
        "impact_level_display",
        "cascade_depth",
        "priority_score",
        "impact_reason",
        "data_quality_warning",
    ]
    existing_cols = [c for c in display_cols if c in affected_ranked.columns]

    affected_display = affected_ranked[existing_cols].copy()
    for tc in ["std", "sta"]:
        if tc in affected_display.columns:
            affected_display[tc] = affected_display[tc].apply(
                lambda t: t.strftime("%H:%M") if t is not None else ""
            )

    st.dataframe(affected_display, use_container_width=True, hide_index=True)

# ─── Aircraft Rotation Table View ──────────────────────────────────────
st.subheader("Aircraft Rotation Detail")

affected_aircraft = affected["aircraft_reg"].unique().tolist() if not affected.empty else []

if affected_aircraft:
    sort_keys = [k for k in ("flight_date", "std") if k in df_result.columns]
    for reg in sorted(str(r) for r in affected_aircraft if r is not None):
        with st.expander(f"Aircraft: {reg}"):
            ac_flights = df_result[df_result["aircraft_reg"] == reg].sort_values(
                sort_keys, na_position="last"
            )
            rotation_cols = [
                "flight_no",
                "origin",
                "destination",
                "flight_date",
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
