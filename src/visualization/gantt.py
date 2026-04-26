"""Plotly Gantt chart for aircraft rotation visualisation.

Each aircraft is one row; each scheduled sector is a horizontal bar from
STD to STA, colour-coded by impact level. The closure window is drawn as
a vertical shaded band.
"""

from __future__ import annotations

from collections.abc import Iterable
from datetime import date, datetime, time, timedelta
from typing import Any

import pandas as pd

from src.models.event import AirportClosureEvent

LEVEL_COLOURS = {
    "Level 1": "#d62728",  # red
    "Level 2": "#ff7f0e",  # orange
    "3+": "#fec44f",  # yellow
    "Not affected": "#1f77b4",  # blue
}


def _combine(d: object, t: object) -> datetime | None:
    if not isinstance(t, time):
        return None
    if isinstance(d, date):
        return datetime.combine(d, t)
    return None


def _row_intervals(row: pd.Series) -> tuple[datetime, datetime] | None:
    """Return (start, end) datetimes for a flight row, or None if missing."""
    flight_date = row.get("flight_date")
    std = row.get("std")
    sta = row.get("sta")

    start = _combine(flight_date, std) if std is not None else None
    end = _combine(flight_date, sta) if sta is not None else None

    if start is None and end is None:
        return None
    if start is None and end is not None:
        start = end - timedelta(hours=2)
    if end is None and start is not None:
        end = start + timedelta(hours=2)
    if end is not None and start is not None and end <= start:
        # Overnight sector — STA is past midnight relative to STD.
        end = end + timedelta(days=1)
    assert start is not None and end is not None
    return start, end


def build_rotation_gantt(
    df: pd.DataFrame,
    events: AirportClosureEvent | Iterable[AirportClosureEvent],
) -> Any:
    """Build a Plotly Figure showing each aircraft's rotation.

    ``events`` may be a single event (back-compat) or an iterable. Each
    event draws its own colour-coded closure band so multi-airport
    scenarios are visually distinguishable on the same chart.

    Returns None if Plotly is not available — callers should handle this
    so the rest of the dashboard still renders.
    """
    if isinstance(events, AirportClosureEvent):
        events_list: list[AirportClosureEvent] = [events]
    else:
        events_list = list(events)
    try:
        import plotly.express as px
        import plotly.graph_objects as go
    except ImportError:
        return None

    if df.empty or "aircraft_reg" not in df.columns:
        return None

    rows: list[dict[str, Any]] = []
    for _, row in df.iterrows():
        reg = row.get("aircraft_reg")
        if reg is None or (isinstance(reg, float) and pd.isna(reg)):
            continue
        interval = _row_intervals(row)
        if interval is None:
            continue
        start, end = interval
        rows.append(
            {
                "aircraft_reg": str(reg),
                "start": start,
                "end": end,
                "flight_no": str(row.get("flight_no", "")),
                "origin": str(row.get("origin", "")),
                "destination": str(row.get("destination", "")),
                "impact_level_display": str(row.get("impact_level_display") or "Not affected"),
            }
        )

    if not rows:
        return None

    plot_df = pd.DataFrame(rows)
    plot_df = plot_df.sort_values(["aircraft_reg", "start"])

    fig = px.timeline(
        plot_df,
        x_start="start",
        x_end="end",
        y="aircraft_reg",
        color="impact_level_display",
        color_discrete_map=LEVEL_COLOURS,
        hover_data={
            "flight_no": True,
            "origin": True,
            "destination": True,
            "start": "|%Y-%m-%d %H:%M",
            "end": "|%Y-%m-%d %H:%M",
            "aircraft_reg": False,
        },
        category_orders={
            "impact_level_display": ["Level 1", "Level 2", "3+", "Not affected"],
        },
    )

    fig.update_yaxes(autorange="reversed", title="Aircraft")
    fig.update_xaxes(title="Time")

    for ev in events_list:
        closure_start = datetime.combine(ev.closure_date, ev.start_time)
        closure_end = datetime.combine(ev.closure_date, ev.end_time)
        # Use the event's type colour at low opacity so overlapping events
        # remain readable.
        hex_colour = ev.closure_type_colour.lstrip("#")
        r, g, b = (int(hex_colour[i : i + 2], 16) for i in (0, 2, 4))
        fillcolor = f"rgba({r}, {g}, {b}, 0.12)"
        fig.add_vrect(
            x0=closure_start,
            x1=closure_end,
            fillcolor=fillcolor,
            line_width=0,
            annotation_text=f"{ev.airport} {ev.closure_type_label.lower()}",
            annotation_position="top left",
        )

    fig.update_layout(
        height=max(320, 28 * plot_df["aircraft_reg"].nunique() + 80),
        legend_title_text="Impact",
        margin={"l": 80, "r": 20, "t": 40, "b": 40},
    )

    # Reference go for consumers that expect Figure type
    assert isinstance(fig, go.Figure)
    return fig
