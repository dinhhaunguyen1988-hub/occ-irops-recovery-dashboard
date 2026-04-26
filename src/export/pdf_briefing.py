"""1-page PDF briefing generator for OCC handoff.

Produces a compact summary that DM can attach to the shift-handover email
or print before the daily IROPS standup. The output is intentionally
single-page so it can be skimmed in 30 seconds.

Returns ``None`` if reportlab is not installed; callers should check.
"""

from __future__ import annotations

from collections.abc import Iterable
from datetime import datetime, timezone
from io import BytesIO

import pandas as pd

from src.models.event import AirportClosureEvent


def build_briefing_pdf(
    df: pd.DataFrame,
    events: Iterable[AirportClosureEvent],
    kpis: dict,
    top_n: int = 10,
) -> BytesIO | None:
    """Render a 1-page PDF briefing.

    Parameters
    ----------
    df : pd.DataFrame
        Cascade-analysed dataframe (must include ``priority_score``).
    events : iterable of AirportClosureEvent
        Closure events covered by the analysis.
    kpis : dict
        Output of :func:`compute_kpis`.
    top_n : int
        Number of priority flights to list (default 10).

    Returns
    -------
    BytesIO | None
        PDF buffer ready for ``st.download_button``, or ``None`` when
        reportlab is not available.
    """
    try:
        from reportlab.lib import colors
        from reportlab.lib.pagesizes import A4
        from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
        from reportlab.lib.units import mm
        from reportlab.platypus import (
            Paragraph,
            SimpleDocTemplate,
            Spacer,
            Table,
            TableStyle,
        )
    except ImportError:
        return None

    events_list = list(events)
    buffer = BytesIO()
    doc = SimpleDocTemplate(
        buffer,
        pagesize=A4,
        leftMargin=15 * mm,
        rightMargin=15 * mm,
        topMargin=12 * mm,
        bottomMargin=12 * mm,
    )

    styles = getSampleStyleSheet()
    h1 = ParagraphStyle("H1", parent=styles["Heading1"], fontSize=16, spaceAfter=4)
    h2 = ParagraphStyle("H2", parent=styles["Heading2"], fontSize=11, spaceAfter=2)
    body = ParagraphStyle("Body", parent=styles["BodyText"], fontSize=9, leading=11)
    small = ParagraphStyle("Small", parent=styles["BodyText"], fontSize=8, textColor=colors.grey)

    story: list = [Paragraph("OCC IROPS Recovery Briefing", h1)]
    story.append(
        Paragraph(
            f"Generated: {datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M UTC')}",
            small,
        )
    )
    story.append(Spacer(1, 4 * mm))

    # --- Closure events ---
    story.append(Paragraph("Closure events", h2))
    if events_list:
        ev_rows: list[list[str]] = [["Airport", "Type", "Date", "Window"]]
        for ev in events_list:
            ev_rows.append(
                [
                    ev.airport,
                    ev.closure_type_label,
                    ev.closure_date.isoformat(),
                    f"{ev.start_time:%H:%M}–{ev.end_time:%H:%M}",
                ]
            )
        ev_table = Table(ev_rows, hAlign="LEFT")
        ev_table.setStyle(
            TableStyle(
                [
                    ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#eeeeee")),
                    ("FONT", (0, 0), (-1, 0), "Helvetica-Bold", 9),
                    ("FONT", (0, 1), (-1, -1), "Helvetica", 9),
                    ("GRID", (0, 0), (-1, -1), 0.25, colors.grey),
                    ("LEFTPADDING", (0, 0), (-1, -1), 4),
                    ("RIGHTPADDING", (0, 0), (-1, -1), 4),
                ]
            )
        )
        story.append(ev_table)
    else:
        story.append(Paragraph("(no events provided)", body))
    story.append(Spacer(1, 4 * mm))

    # --- KPI summary ---
    story.append(Paragraph("Summary KPIs", h2))
    kpi_rows: list[list[str]] = [
        ["Total Flights", str(kpis.get("total_flights", "—"))],
        ["Affected Flights", str(kpis.get("affected_flights", "—"))],
        ["Level 1", str(kpis.get("level_1_count", "—"))],
        ["Level 2", str(kpis.get("level_2_count", "—"))],
        ["Level 3+", str(kpis.get("level_3plus_count", "—"))],
        ["Aircraft Affected", str(kpis.get("aircraft_affected", "—"))],
    ]
    if "total_pax_disrupted" in kpis:
        kpi_rows.append(["Pax Disrupted (est.)", f"{int(kpis['total_pax_disrupted']):,}"])
    if "total_cost_usd" in kpis:
        kpi_rows.append(["Cost Impact (est. USD)", f"${kpis['total_cost_usd']:,.0f}"])
    kpi_table = Table(kpi_rows, hAlign="LEFT", colWidths=[60 * mm, 40 * mm])
    kpi_table.setStyle(
        TableStyle(
            [
                ("FONT", (0, 0), (-1, -1), "Helvetica", 9),
                ("BACKGROUND", (0, 0), (0, -1), colors.HexColor("#fafafa")),
                ("LEFTPADDING", (0, 0), (-1, -1), 4),
                ("RIGHTPADDING", (0, 0), (-1, -1), 4),
            ]
        )
    )
    story.append(kpi_table)
    story.append(Spacer(1, 4 * mm))

    # --- Top-N priority flights ---
    story.append(Paragraph(f"Top {top_n} priority flights", h2))
    if df.empty or "priority_score" not in df.columns:
        story.append(Paragraph("(no flights to rank)", body))
    else:
        affected = df[df["impact_level_numeric"].notna()].copy()
        affected = affected.sort_values("priority_score", ascending=False).head(top_n)

        cols = [
            ("flight_no", "Flight"),
            ("aircraft_reg", "Reg"),
            ("origin", "From"),
            ("destination", "To"),
            ("std", "STD"),
            ("impact_level_display", "Level"),
            ("cascade_depth", "Depth"),
            ("priority_score", "Score"),
            ("est_pax", "Pax"),
            ("est_cost_usd", "Cost (USD)"),
        ]
        existing = [(k, label) for k, label in cols if k in affected.columns]

        header = [label for _, label in existing]
        body_rows: list[list[str]] = [header]
        for _, r in affected.iterrows():
            row: list[str] = []
            for k, _ in existing:
                v = r.get(k)
                if k in {"std", "sta"} and v is not None:
                    try:
                        row.append(v.strftime("%H:%M"))
                        continue
                    except (AttributeError, TypeError):
                        pass
                if k == "est_cost_usd" and pd.notna(v):
                    row.append(f"${float(v):,.0f}")
                    continue
                if v is None or (isinstance(v, float) and pd.isna(v)):
                    row.append("")
                else:
                    row.append(str(v))
            body_rows.append(row)

        flight_table = Table(body_rows, hAlign="LEFT", repeatRows=1)
        flight_table.setStyle(
            TableStyle(
                [
                    ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#eeeeee")),
                    ("FONT", (0, 0), (-1, 0), "Helvetica-Bold", 8),
                    ("FONT", (0, 1), (-1, -1), "Helvetica", 8),
                    ("GRID", (0, 0), (-1, -1), 0.25, colors.lightgrey),
                    ("LEFTPADDING", (0, 0), (-1, -1), 3),
                    ("RIGHTPADDING", (0, 0), (-1, -1), 3),
                ]
            )
        )
        story.append(flight_table)

    story.append(Spacer(1, 5 * mm))
    story.append(
        Paragraph(
            "Generated by OCC IROPS Recovery Dashboard. "
            "All pax / cost figures are rule-based estimates — review with current load-factor data before action.",
            small,
        )
    )

    doc.build(story)
    buffer.seek(0)
    return buffer
