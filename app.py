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

from src.auth import is_auth_disabled, require_login, role_can_edit_settings, role_can_view_audit
from src.cascade.cascade_detector import compute_kpis, detect_cascade_multi
from src.cascade.ranking import compute_priority
from src.config import MVP_LIMITATION_WARNING
from src.decision import (
    StressScenario,
    build_reaccommodation_list,
    run_stress_test,
    suggest_recovery_options,
)
from src.export.excel_exporter import export_to_excel
from src.export.pdf_briefing import build_briefing_pdf
from src.i18n import available_locales, set_locale, t
from src.impact import estimate_pax_and_cost
from src.logging_config import get_logger, setup_logging
from src.models.event import CLOSURE_TYPES, AirportClosureEvent
from src.parser.multi_file import parse_multiple_dayrep_reports
from src.persistence import (
    get_connection,
    get_settings,
    init_db,
    list_audit_events,
    list_recent_runs,
    record_audit_event,
    record_run,
    update_settings,
)
from src.persistence.settings import settings_to_estimator_kwargs
from src.validation import (
    PREDICTED_LABELS,
    parse_actuals_csv,
    validate_against_actuals,
)
from src.visualization.gantt import build_rotation_gantt
from src.visualization.map_view import build_airport_map

setup_logging()
logger = get_logger(__name__)

st.set_page_config(page_title="OCC IROPS Recovery Dashboard", layout="wide")

# ─── Auth gate ─────────────────────────────────────────────────────────
user = require_login()
if user is None:
    st.stop()
if is_auth_disabled():
    st.sidebar.warning("Auth disabled (OCC_AUTH_DISABLED=1) — local dev mode.")
st.sidebar.success(f"Signed in as **{user.name}** ({user.role})")

# ─── Persistence bootstrap ─────────────────────────────────────────────
db_conn = get_connection()
init_db(db_conn)
settings_blob = get_settings(db_conn)
estimator_kwargs = settings_to_estimator_kwargs(settings_blob)

# ─── Locale toggle (must come before any t(...) call below) ────────────
locales = available_locales()
locale_choice = st.sidebar.selectbox(
    "🌐 Language / Ngôn ngữ",
    options=locales,
    index=0,
    format_func=lambda c: {"vi": "Tiếng Việt", "en": "English"}.get(c, c),
)
set_locale(locale_choice)

# ─── Sidebar ────────────────────────────────────────────────────────────
st.sidebar.title(t("sidebar.title"))
st.sidebar.markdown("---")

uploaded_files = st.sidebar.file_uploader(
    "Upload DayRepReport(s) (Excel)",
    type=["xlsx", "xls"],
    accept_multiple_files=True,
    help="Upload the closure-day file plus the next-day file to capture overnight cascade.",
)

st.sidebar.markdown("**Closure events**")
n_events = st.sidebar.number_input(
    "Number of closure events",
    min_value=1,
    max_value=5,
    value=1,
    help="Multi-airport closure: typhoon may close HAN+HPH at the same time, etc.",
)

closure_type_keys = list(CLOSURE_TYPES.keys())
closure_type_labels = {k: CLOSURE_TYPES[k]["label"] for k in closure_type_keys}

event_inputs: list[dict] = []
for i in range(int(n_events)):
    with st.sidebar.expander(f"Event #{i + 1}", expanded=(i == 0)):
        airport = st.text_input("Airport Code", value="HAN" if i == 0 else "", key=f"ev{i}_ap")
        closure_dt = st.date_input("Closure Date", value=date(2026, 4, 24), key=f"ev{i}_dt")
        c_start = st.time_input("Closure Start Time", value=time(14, 0), key=f"ev{i}_start")
        c_end = st.time_input("Closure End Time", value=time(18, 0), key=f"ev{i}_end")
        c_type = st.selectbox(
            "Closure Type",
            options=closure_type_keys,
            format_func=lambda k: closure_type_labels[k],
            index=0,
            key=f"ev{i}_type",
        )
        event_inputs.append(
            {
                "airport": airport,
                "closure_date": closure_dt,
                "start_time": c_start,
                "end_time": c_end,
                "closure_type": c_type,
            }
        )

st.sidebar.markdown("---")
whatif_enabled = st.sidebar.checkbox(
    "What-if mode",
    value=False,
    help="Compare the baseline closure window (event #1) with an alternative one.",
)
whatif_start = event_inputs[0]["start_time"]
whatif_end = event_inputs[0]["end_time"]
if whatif_enabled:
    whatif_start = st.sidebar.time_input(
        "What-if Start Time", value=event_inputs[0]["start_time"], key="wi_start"
    )
    whatif_end = st.sidebar.time_input(
        "What-if End Time", value=event_inputs[0]["end_time"], key="wi_end"
    )

run_analysis = st.sidebar.button("Run Analysis", type="primary")

# ─── Main area ──────────────────────────────────────────────────────────
st.title(t("app.title"))

st.warning(MVP_LIMITATION_WARNING)

if not uploaded_files:
    st.info("Upload one or more DayRepReport files in the sidebar to begin analysis.")
    st.stop()

if not run_analysis:
    st.info("Configure parameters in the sidebar and click **Run Analysis**.")
    st.stop()

# ─── Validate events ────────────────────────────────────────────────────
events: list[AirportClosureEvent] = []
for i, inp in enumerate(event_inputs):
    if not inp["airport"].strip():
        st.error(f"Event #{i + 1}: airport code is required.")
        st.stop()
    try:
        events.append(AirportClosureEvent(**inp))
    except ValueError as e:
        st.error(f"Event #{i + 1}: {e}")
        st.stop()

# Baseline = event #1; what-if reuses its airport/date/type with new times
whatif_event: AirportClosureEvent | None = None
if whatif_enabled:
    base = events[0]
    try:
        whatif_event = AirportClosureEvent(
            airport=base.airport,
            closure_date=base.closure_date,
            start_time=whatif_start,
            end_time=whatif_end,
            closure_type=base.closure_type,
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
        "events": [str(e) for e in events],
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
    df_result = detect_cascade_multi(df, events)
    df_result = compute_priority(df_result)
    df_result = estimate_pax_and_cost(df_result, **estimator_kwargs)  # type: ignore[arg-type]
    kpis = compute_kpis(df_result)

affected = df_result[df_result["impact_level_numeric"].notna()].copy()

# Augment KPIs with pax/cost roll-ups
kpis["total_pax_disrupted"] = int(affected["est_pax"].sum()) if not affected.empty else 0
kpis["total_cost_usd"] = float(affected["est_cost_usd"].sum()) if not affected.empty else 0.0

logger.info(
    "cascade_completed",
    extra={
        "file_hashes": file_hashes,
        "events": [str(e) for e in events],
        **{f"kpi_{k}": v for k, v in kpis.items() if isinstance(v, (int, float))},
    },
)

# Persist this run + audit event so DMs can review history later.
try:
    closure_config_payload = [
        {
            "airport": e.airport,
            "closure_date": str(e.closure_date),
            "start_time": e.start_time.strftime("%H:%M"),
            "end_time": e.end_time.strftime("%H:%M"),
            "closure_type": e.closure_type,
        }
        for e in events
    ]
    run_id = record_run(
        db_conn,
        user=user.username,
        file_hashes=file_hashes,
        closure_config=closure_config_payload,
        kpi_snapshot={k: v for k, v in kpis.items() if isinstance(v, (int, float))},
    )
    record_audit_event(
        db_conn,
        user=user.username,
        action="run_analysis",
        payload={"run_id": run_id, "events": closure_config_payload},
    )
except Exception as exc:  # noqa: BLE001 — never crash UI on persistence error
    logger.warning("persistence_failed", extra={"error": str(exc)})

# ─── What-if comparison ────────────────────────────────────────────────
whatif_diff: dict[str, set[str]] = {}
if whatif_event is not None:
    df_whatif = detect_cascade_multi(df, [whatif_event])
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
for ev in events:
    st.caption(f"Event: {ev}")
if len(uploaded_files) > 1:
    st.caption(f"Multi-file run: {len(uploaded_files)} files merged for overnight cascade.")
if len(events) > 1:
    st.caption(f"Multi-airport run: {len(events)} concurrent closure events.")

col1, col2, col3, col4, col5 = st.columns(5)
col1.metric("Total Flights", kpis["total_flights"])
col2.metric("Affected Flights", kpis["affected_flights"])
col3.metric("Level 1", kpis["level_1_count"])
col4.metric("Level 2", kpis["level_2_count"])
col5.metric("Level 3+", kpis["level_3plus_count"])

col6, col7, col8 = st.columns(3)
col6.metric("Aircraft Affected", kpis["aircraft_affected"])
col7.metric("Pax Disrupted (est.)", f"{kpis['total_pax_disrupted']:,}")
col8.metric("Cost Impact (est. USD)", f"${kpis['total_cost_usd']:,.0f}")

st.caption(
    "Pax / cost are rule-based estimates "
    "(seat config × 0.85 load factor × per-level delay × $0.50/pax/min). "
    "Tune assumptions in `src/impact/pax_estimator.py`."
)

# ─── Top-10 highlight cards ────────────────────────────────────────────
if not affected.empty:
    st.subheader("Top-10 highlights")
    top_col1, top_col2, top_col3 = st.columns(3)

    short_cols = [
        c
        for c in (
            "flight_no",
            "aircraft_reg",
            "origin",
            "destination",
            "impact_level_display",
        )
        if c in affected.columns
    ]

    def _short(df_in: pd.DataFrame, value_col: str) -> pd.DataFrame:
        cols = short_cols + [value_col]
        existing = [c for c in cols if c in df_in.columns]
        return df_in[existing].head(10)

    with top_col1:
        st.markdown("**By pax disrupted**")
        st.dataframe(
            _short(affected.sort_values("est_pax", ascending=False), "est_pax"),
            use_container_width=True,
            hide_index=True,
        )
    with top_col2:
        st.markdown("**By cost impact (USD)**")
        cost_top = affected.sort_values("est_cost_usd", ascending=False).head(10).copy()
        if "est_cost_usd" in cost_top.columns:
            cost_top["est_cost_usd"] = cost_top["est_cost_usd"].apply(lambda v: f"${v:,.0f}")
        st.dataframe(_short(cost_top, "est_cost_usd"), use_container_width=True, hide_index=True)
    with top_col3:
        st.markdown("**By cascade depth**")
        depth_top = affected[affected["cascade_depth"] > 0].sort_values(
            "cascade_depth", ascending=False
        )
        st.dataframe(
            _short(depth_top, "cascade_depth"),
            use_container_width=True,
            hide_index=True,
        )

# ─── What-if diff panel ────────────────────────────────────────────────
if whatif_event is not None:
    st.subheader("What-if Comparison")
    st.caption(f"Baseline: {events[0]}")
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
        win_text = " · ".join(
            f"{e.airport} {e.start_time:%H:%M}–{e.end_time:%H:%M}" for e in events
        )
        st.caption(f"Closure windows: {win_text}")

# ─── Map view ──────────────────────────────────────────────────────────
st.subheader("Network Map")
map_fig = build_airport_map(df_result, events)
if map_fig is None:
    st.info("Map unavailable (Plotly missing or no recognised airports in data).")
else:
    st.plotly_chart(map_fig, use_container_width=True)

# ─── Aircraft Rotation Gantt ───────────────────────────────────────────
st.subheader("Aircraft Rotation Gantt")
if affected.empty:
    st.info("No affected aircraft to plot.")
else:
    affected_regs = set(affected["aircraft_reg"].dropna().astype(str).tolist())
    rotation_df = df_result[df_result["aircraft_reg"].astype(str).isin(affected_regs)].copy()
    fig = build_rotation_gantt(rotation_df, events)
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
        "est_pax",
        "est_cost_usd",
        "impact_reason",
        "impact_explanation",
        "data_quality_warning",
    ]
    existing_cols = [c for c in display_cols if c in affected_ranked.columns]

    affected_display = affected_ranked[existing_cols].copy()
    for tc in ["std", "sta"]:
        if tc in affected_display.columns:
            affected_display[tc] = affected_display[tc].apply(
                lambda t: t.strftime("%H:%M") if t is not None else ""
            )
    if "est_cost_usd" in affected_display.columns:
        affected_display["est_cost_usd"] = affected_display["est_cost_usd"].apply(
            lambda v: f"${v:,.0f}"
        )

    st.dataframe(affected_display, use_container_width=True, hide_index=True)

# ─── Decision Support (Sprint 7) ───────────────────────────────────────
with st.expander("Decision support — recovery options & reaccommodation", expanded=False):
    st.caption(
        "Advisory only. Rule-based suggestions to surface options the DM might "
        "miss during a fast-moving event. Final decisions remain with OCC."
    )

    if affected.empty:
        st.info("No affected flights — no recovery options to suggest.")
    else:
        # Recovery options per L1
        first_event_end = events[0].end_time
        closure_end_minutes = first_event_end.hour * 60 + first_event_end.minute
        recovery_opts = suggest_recovery_options(df_result, closure_end_minutes=closure_end_minutes)
        if recovery_opts:
            st.markdown("**Recovery options (per Level-1 flight, sorted best→worst)**")
            recovery_df = pd.DataFrame(
                [
                    {
                        "flight_no": o.flight_no,
                        "aircraft_reg": o.aircraft_reg,
                        "option": o.option,
                        "swap_to": o.swap_candidate_reg or "",
                        "pax": o.pax_affected,
                        "cost_usd": round(o.cost_usd, 2),
                        "score": round(o.score, 1),
                        "description": o.description,
                    }
                    for o in recovery_opts
                ]
            )
            st.dataframe(recovery_df, use_container_width=True, hide_index=True)
        else:
            st.info("No Level-1 flights — no recovery options to suggest.")

        # Pax reaccommodation list
        st.markdown("**Pax reaccommodation priority list**")
        reaccom = build_reaccommodation_list(df_result)
        if reaccom:
            reaccom_df = pd.DataFrame(
                [
                    {
                        "rank": r.rank,
                        "flight_no": r.flight_no,
                        "aircraft_reg": r.aircraft_reg,
                        "route": f"{r.origin} → {r.destination}",
                        "intl": "✓" if r.is_international else "",
                        "level": r.impact_level,
                        "depth": r.cascade_depth,
                        "pax": r.est_pax,
                        "rationale": r.rationale,
                    }
                    for r in reaccom
                ]
            )
            st.dataframe(reaccom_df, use_container_width=True, hide_index=True)
        else:
            st.info("No affected flights to reaccommodate.")

# ─── Network Stress Test (Sprint 7) ────────────────────────────────────
with st.expander("Network stress test (multi-day what-if)", expanded=False):
    st.caption(
        "Project the current closure scenario across N days and combine "
        "airports to estimate worst-case multi-day impact. Uses the loaded "
        "schedule as the proxy for every day."
    )
    col_a, col_b, col_c = st.columns(3)
    stress_airports = col_a.multiselect(
        "Airports to close (simultaneously each day)",
        options=sorted({e.airport for e in events}) or ["HAN"],
        default=[events[0].airport] if events else ["HAN"],
    )
    stress_days = col_b.number_input("Number of days", min_value=1, max_value=7, value=3, step=1)
    stress_start_date = col_c.date_input(
        "Scenario start date", value=events[0].closure_date if events else None
    )
    if st.button("Run stress test"):
        scenario = StressScenario(
            airports=tuple(stress_airports),
            start_date=stress_start_date,
            duration_days=int(stress_days),
            closure_start=events[0].start_time,
            closure_end=events[0].end_time,
            closure_type=events[0].closure_type,
        )
        with st.spinner(f"Running {stress_days}-day stress test..."):
            stress_result = run_stress_test(df, scenario)

        if not stress_result.per_day:
            st.warning("Empty result — check inputs.")
        else:
            st.markdown("**Per-day KPIs**")
            st.dataframe(
                pd.DataFrame(stress_result.per_day),
                use_container_width=True,
                hide_index=True,
            )
            st.markdown("**Aggregate totals across the scenario**")
            totals = stress_result.totals
            tcol1, tcol2, tcol3, tcol4 = st.columns(4)
            tcol1.metric("Total affected", totals.get("affected_flights", 0))
            tcol2.metric("Total pax disrupted", totals.get("total_pax_disrupted", 0))
            tcol3.metric("Total cost (USD)", f"${totals.get('total_cost_usd', 0):,.0f}")
            if stress_result.worst_day is not None:
                tcol4.metric(
                    "Worst day cost (USD)",
                    f"${float(stress_result.worst_day.get('total_cost_usd', 0)):,.0f}",
                )

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
                "impact_explanation",
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

# ─── Export Excel + PDF ────────────────────────────────────────────────
st.subheader("Export")

excel_buffer = export_to_excel(df_result, events[0], kpis, parse_warnings)
exp_col1, exp_col2 = st.columns(2)
with exp_col1:
    st.download_button(
        label="Download Excel Report",
        data=excel_buffer,
        file_name=f"IROPS_Report_{events[0].airport}_{events[0].closure_date}.xlsx",
        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        type="primary",
    )

with exp_col2:
    pdf_buffer = build_briefing_pdf(df_result, events, kpis, top_n=10)
    if pdf_buffer is None:
        st.info("PDF unavailable (reportlab not installed).")
    else:
        st.download_button(
            label="Download 1-page PDF Briefing",
            data=pdf_buffer,
            file_name=f"IROPS_Briefing_{events[0].airport}_{events[0].closure_date}.pdf",
            mime="application/pdf",
        )

# ─── Validation vs actuals (pilot readiness) ─────────────────────────────
st.subheader("Validation vs Actuals")
st.caption(
    "Upload an `actuals.csv` with columns `flight_no, actual_outcome` "
    "(`on_time | delayed | cancelled | diverted`) to compare predictions "
    "against what actually happened. Optional `flight_date` column for multi-day runs."
)
actuals_file = st.file_uploader(
    "Actuals CSV",
    type=["csv"],
    key="actuals_uploader",
)
if actuals_file is not None:
    try:
        actuals_df = parse_actuals_csv(actuals_file)
    except (ValueError, pd.errors.ParserError) as exc:
        st.error(f"Could not parse actuals CSV: {exc}")
    else:
        result = validate_against_actuals(df_result, actuals_df)
        cov = result["coverage"].set_index("metric")["count"].to_dict()
        st.caption(
            f"Coverage: {cov.get('matched', 0)} / {cov.get('predictions', 0)} "
            f"flights matched ({cov.get('unmatched', 0)} unmatched)."
        )
        confusion = result["confusion"]
        if confusion.empty:
            st.info("No matched rows — cannot compute confusion matrix.")
        else:
            confusion_pivot = (
                confusion.pivot(
                    index="predicted_label",
                    columns="actual_outcome",
                    values="count",
                )
                .fillna(0)
                .astype(int)
            )
            confusion_pivot = confusion_pivot.reindex(
                index=[lbl for lbl in PREDICTED_LABELS if lbl in confusion_pivot.index]
            )
            st.markdown("**Confusion matrix** (rows = predicted, columns = actual)")
            st.dataframe(confusion_pivot, use_container_width=True)
            st.markdown("**Per-level metrics**")
            st.dataframe(result["metrics"], use_container_width=True, hide_index=True)
            logger.info(
                "validation_completed",
                extra={
                    "file_hashes": file_hashes,
                    "matched": cov.get("matched", 0),
                    "unmatched": cov.get("unmatched", 0),
                },
            )

# ─── Recent runs (history) ─────────────────────────────────────────────
with st.expander("Recent runs (history)", expanded=False):
    runs = list_recent_runs(db_conn, limit=10)
    if not runs:
        st.info("No prior runs recorded yet.")
    else:
        runs_df = pd.DataFrame(
            [
                {
                    "id": r["id"],
                    "user": r["user"],
                    "created_at": r["created_at"],
                    "events": ", ".join(
                        f"{e['airport']} {e['start_time']}-{e['end_time']} ({e['closure_date']})"
                        for e in r["closure_config"]
                    ),
                    "affected": r["kpi_snapshot"].get("affected_flights"),
                    "L1": r["kpi_snapshot"].get("level_1_count"),
                    "L2": r["kpi_snapshot"].get("level_2_count"),
                    "L3+": r["kpi_snapshot"].get("level_3plus_count"),
                    "pax": r["kpi_snapshot"].get("total_pax_disrupted"),
                    "cost_usd": r["kpi_snapshot"].get("total_cost_usd"),
                }
                for r in runs
            ]
        )
        st.dataframe(runs_df, use_container_width=True, hide_index=True)

# ─── Settings (DM-only) ────────────────────────────────────────────────
if role_can_edit_settings(user.role):
    with st.expander("Settings (DM-only)", expanded=False):
        st.caption(
            "Tunable assumptions for pax / cost estimation. Changes apply to the next "
            "Run Analysis click and are persisted to the local SQLite database."
        )
        new_load_factor = st.slider(
            "Load factor",
            min_value=0.5,
            max_value=1.0,
            value=float(settings_blob["load_factor"]),
            step=0.01,
        )
        new_cost = st.number_input(
            "Cost per pax per minute (USD)",
            min_value=0.0,
            max_value=5.0,
            value=float(settings_blob["cost_per_pax_per_minute"]),
            step=0.05,
        )
        st.markdown("**Aircraft seat capacity**")
        cap_df = pd.DataFrame(
            sorted(settings_blob["seat_capacity"].items()),
            columns=["aircraft_type", "seat_capacity"],
        )
        edited_cap = st.data_editor(
            cap_df,
            num_rows="dynamic",
            use_container_width=True,
            key="capacity_editor",
        )
        if st.button("Save settings", type="primary"):
            new_capacity = {
                str(row["aircraft_type"]).strip().upper(): int(row["seat_capacity"])
                for _, row in edited_cap.iterrows()
                if pd.notna(row["aircraft_type"]) and pd.notna(row["seat_capacity"])
            }
            new_blob = {
                "load_factor": new_load_factor,
                "cost_per_pax_per_minute": new_cost,
                "seat_capacity": new_capacity,
                "level_delay_minutes": settings_blob["level_delay_minutes"],
            }
            update_settings(db_conn, new_blob, updated_by=user.username)  # type: ignore[arg-type]
            record_audit_event(
                db_conn,
                user=user.username,
                action="settings_updated",
                payload={"load_factor": new_load_factor, "cost": new_cost},
            )
            st.success("Settings saved. Click **Run Analysis** to re-compute with the new values.")

# ─── Audit log (DM-only) ───────────────────────────────────────────────
if role_can_view_audit(user.role):
    with st.expander("Audit log (DM-only)", expanded=False):
        events_log = list_audit_events(db_conn, limit=200)
        if not events_log:
            st.info("No audit events yet.")
        else:
            audit_df = pd.DataFrame(events_log)
            st.dataframe(audit_df, use_container_width=True, hide_index=True)
            csv_buf = audit_df.to_csv(index=False).encode("utf-8")
            st.download_button(
                label="Download audit log (CSV)",
                data=csv_buf,
                file_name="audit_log.csv",
                mime="text/csv",
            )
