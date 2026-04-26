"""Plotly scattergeo map of airports involved in an IROPS scenario.

- Closed airports (any event) -> red marker labelled with closure window
- Other airports touched by affected flights -> orange marker
- Unaffected airports referenced by the data -> light blue marker

Returns ``None`` when Plotly is missing or no airports map to known
coordinates so callers degrade gracefully.
"""

from __future__ import annotations

from collections.abc import Iterable
from typing import Any

import pandas as pd

from src.models.event import AirportClosureEvent
from src.visualization.airport_coords import get_coords


def _airports_in_df(df: pd.DataFrame, mask: pd.Series | None = None) -> set[str]:
    """Return the union of origin/destination IATA codes (uppercased)."""
    sub = df if mask is None else df[mask]
    out: set[str] = set()
    for col in ("origin", "destination"):
        if col not in sub.columns:
            continue
        out.update(str(v).strip().upper() for v in sub[col].dropna().tolist() if str(v).strip())
    return out


def build_airport_map(
    df: pd.DataFrame,
    events: Iterable[AirportClosureEvent],
) -> Any:
    """Build a Plotly scattergeo figure showing airports involved.

    Returns ``None`` if Plotly is unavailable or no plottable airports.
    """
    try:
        import plotly.graph_objects as go
    except ImportError:
        return None

    events_list = list(events)
    closed_airports = {e.airport.upper() for e in events_list}

    affected_mask = (
        df["impact_level_numeric"].notna()
        if "impact_level_numeric" in df.columns
        else pd.Series(False, index=df.index)
    )

    affected_airports = _airports_in_df(df, affected_mask) - closed_airports
    all_airports = _airports_in_df(df) - closed_airports - affected_airports

    def _to_traces(codes: set[str], colour: str, name: str, size: int) -> dict[str, Any] | None:
        lats: list[float] = []
        lons: list[float] = []
        texts: list[str] = []
        for code in sorted(codes):
            coords = get_coords(code)
            if coords is None:
                continue
            lats.append(coords[0])
            lons.append(coords[1])
            texts.append(code)
        if not lats:
            return None
        return {
            "type": "scattergeo",
            "lon": lons,
            "lat": lats,
            "text": texts,
            "name": name,
            "marker_color": colour,
            "marker_size": size,
            "size_value": size,
        }

    closed_trace_data = _to_traces(closed_airports, "#d62728", "Closed", 14)
    affected_trace_data = _to_traces(affected_airports, "#ff7f0e", "Affected", 9)
    other_trace_data = _to_traces(all_airports, "#1f77b4", "Other", 6)

    traces: list[Any] = []
    closed_labels = []
    if closed_trace_data is not None:
        # Add closure-window annotation to closed-airport hover text.
        per_airport_event = {e.airport.upper(): e for e in events_list}
        closed_hover = []
        for code in closed_trace_data["text"]:
            ev = per_airport_event.get(code)
            if ev is not None:
                closed_hover.append(
                    f"{code}<br>{ev.closure_type_label}"
                    f"<br>{ev.start_time:%H:%M}–{ev.end_time:%H:%M}"
                    f"<br>{ev.closure_date}"
                )
                closed_labels.append(code)
            else:
                closed_hover.append(code)
        traces.append(
            go.Scattergeo(
                lon=closed_trace_data["lon"],
                lat=closed_trace_data["lat"],
                text=closed_trace_data["text"],
                hovertext=closed_hover,
                hoverinfo="text",
                name="Closed",
                marker={"color": closed_trace_data["marker_color"], "size": 14, "symbol": "x"},
                mode="markers+text",
                textposition="top center",
            )
        )
    if affected_trace_data is not None:
        traces.append(
            go.Scattergeo(
                lon=affected_trace_data["lon"],
                lat=affected_trace_data["lat"],
                text=affected_trace_data["text"],
                hovertext=affected_trace_data["text"],
                hoverinfo="text",
                name="Affected",
                marker={"color": affected_trace_data["marker_color"], "size": 9},
                mode="markers+text",
                textposition="top center",
            )
        )
    if other_trace_data is not None:
        traces.append(
            go.Scattergeo(
                lon=other_trace_data["lon"],
                lat=other_trace_data["lat"],
                text=other_trace_data["text"],
                hoverinfo="text",
                name="Other",
                marker={"color": other_trace_data["marker_color"], "size": 6, "opacity": 0.6},
                mode="markers",
            )
        )

    if not traces:
        return None

    fig = go.Figure(data=traces)
    fig.update_layout(
        geo={
            "scope": "asia",
            "showland": True,
            "landcolor": "#f7f7f7",
            "showcountries": True,
            "countrycolor": "#cccccc",
            "showcoastlines": True,
            "coastlinecolor": "#cccccc",
            "fitbounds": "locations",
        },
        height=420,
        margin={"l": 10, "r": 10, "t": 30, "b": 10},
        legend_title_text="Airport role",
    )

    return fig
