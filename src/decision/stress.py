"""Network stress test — scale a closure scenario across days/airports.

Lets the DM ask "what if HAN+SGN cùng đóng 14–18 trong 3 ngày?" and
get worst-case KPIs without manually re-running the analysis day by
day.

This is a *what-if* tool, not a forecast: it re-uses the same flight
schedule across days (since we don't have a multi-day schedule
loader) and aggregates per-day KPIs. It's still useful for showing
the order-of-magnitude impact of a multi-day closure to senior
management.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date, time, timedelta

import pandas as pd

from src.cascade.cascade_detector import compute_kpis, detect_cascade_multi
from src.cascade.ranking import compute_priority
from src.impact import estimate_pax_and_cost
from src.models.event import AirportClosureEvent


@dataclass(frozen=True)
class StressScenario:
    """Definition of a multi-day, multi-airport closure scenario."""

    airports: tuple[str, ...]
    start_date: date
    duration_days: int
    closure_start: time
    closure_end: time
    closure_type: str = "airport_closed"


@dataclass
class StressResult:
    """Aggregated worst-case KPIs across every day of the scenario."""

    per_day: list[dict[str, int | float | str]] = field(default_factory=list)
    worst_day: dict[str, int | float | str] | None = None
    totals: dict[str, int | float] = field(default_factory=dict)


def run_stress_test(
    df: pd.DataFrame,
    scenario: StressScenario,
) -> StressResult:
    """Apply ``scenario`` to ``df`` and return per-day + aggregate KPIs.

    Each day is computed independently against the same flight-schedule
    DataFrame (representing a "typical" day for the airline). For
    multi-airport scenarios, all listed airports close simultaneously
    each day.
    """
    result = StressResult()
    if df.empty or scenario.duration_days <= 0:
        return result

    for offset in range(scenario.duration_days):
        day = scenario.start_date + timedelta(days=offset)
        events = [
            AirportClosureEvent(
                airport=ap,
                closure_date=day,
                start_time=scenario.closure_start,
                end_time=scenario.closure_end,
                closure_type=scenario.closure_type,
            )
            for ap in scenario.airports
        ]
        # Override flight_date so cascade detector treats every flight
        # as happening on the simulated day. Operating on a copy keeps
        # the input DataFrame untouched.
        scratch = df.copy()
        scratch["flight_date"] = day

        scratch = detect_cascade_multi(scratch, events)
        scratch = compute_priority(scratch)
        scratch = estimate_pax_and_cost(scratch)
        kpis = compute_kpis(scratch)
        affected = scratch[scratch["impact_level_numeric"].notna()]
        kpis["total_pax_disrupted"] = int(affected["est_pax"].sum()) if not affected.empty else 0
        kpis["total_cost_usd"] = (
            float(affected["est_cost_usd"].sum()) if not affected.empty else 0.0
        )
        kpis["day"] = day.isoformat()
        result.per_day.append(kpis)

    # Worst day = highest cost.
    if result.per_day:
        result.worst_day = max(result.per_day, key=lambda k: float(k.get("total_cost_usd", 0) or 0))

    # Aggregate totals across the scenario.
    totals = {
        "affected_flights": 0,
        "level_1_count": 0,
        "level_2_count": 0,
        "level_3plus_count": 0,
        "total_pax_disrupted": 0,
        "total_cost_usd": 0.0,
    }
    for k in result.per_day:
        for key in totals:
            v = k.get(key, 0) or 0
            try:
                totals[key] = totals[key] + (float(v) if "cost" in key else int(v))
            except (TypeError, ValueError):
                continue
    # Cost stays float, others int.
    result.totals = {
        "affected_flights": int(totals["affected_flights"]),
        "level_1_count": int(totals["level_1_count"]),
        "level_2_count": int(totals["level_2_count"]),
        "level_3plus_count": int(totals["level_3plus_count"]),
        "total_pax_disrupted": int(totals["total_pax_disrupted"]),
        "total_cost_usd": float(totals["total_cost_usd"]),
    }
    return result
