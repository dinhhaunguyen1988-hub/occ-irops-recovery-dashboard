"""Tests for src.export.pdf_briefing."""

from datetime import date, time

import pandas as pd

from src.cascade.cascade_detector import compute_kpis, detect_cascade
from src.cascade.ranking import compute_priority
from src.export.pdf_briefing import build_briefing_pdf
from src.impact import estimate_pax_and_cost
from src.models.event import AirportClosureEvent


def _han_event() -> AirportClosureEvent:
    return AirportClosureEvent(
        airport="HAN",
        closure_date=date(2026, 4, 24),
        start_time=time(14, 0),
        end_time=time(18, 0),
    )


def _sample_df() -> pd.DataFrame:
    return pd.DataFrame(
        [
            {
                "flight_no": "VN1",
                "aircraft_reg": "VN-A1",
                "aircraft_type": "A321",
                "origin": "SGN",
                "destination": "HAN",
                "std": time(13, 30),
                "sta": time(15, 30),
                "flight_date": date(2026, 4, 24),
            },
            {
                "flight_no": "VN2",
                "aircraft_reg": "VN-A1",
                "aircraft_type": "A321",
                "origin": "HAN",
                "destination": "SGN",
                "std": time(16, 30),
                "sta": time(18, 30),
                "flight_date": date(2026, 4, 24),
            },
        ]
    )


def test_build_briefing_pdf_returns_buffer():
    df = _sample_df()
    ev = _han_event()
    df = detect_cascade(df, ev)
    df = compute_priority(df)
    df = estimate_pax_and_cost(df)
    kpis = compute_kpis(df)
    kpis["total_pax_disrupted"] = int(df["est_pax"].sum())
    kpis["total_cost_usd"] = float(df["est_cost_usd"].sum())

    buf = build_briefing_pdf(df, [ev], kpis, top_n=5)
    assert buf is not None
    data = buf.getvalue()
    # PDF magic header
    assert data[:4] == b"%PDF"
    # Should be non-trivial size (several hundred bytes minimum)
    assert len(data) > 500


def test_briefing_pdf_handles_empty_dataframe():
    """No affected flights still produces a PDF (the briefing notes this)."""
    df = _sample_df()
    ev = AirportClosureEvent(
        airport="ZZZ",  # no flights touch ZZZ → no affected
        closure_date=date(2026, 4, 24),
        start_time=time(14, 0),
        end_time=time(18, 0),
    )
    df = detect_cascade(df, ev)
    df = compute_priority(df)
    df = estimate_pax_and_cost(df)
    kpis = compute_kpis(df)
    buf = build_briefing_pdf(df, [ev], kpis, top_n=5)
    assert buf is not None
    assert buf.getvalue()[:4] == b"%PDF"
