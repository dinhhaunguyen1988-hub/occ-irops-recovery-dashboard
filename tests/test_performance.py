"""Performance smoke test for cascade detection on a large synthetic fleet.

Acceptance criteria for Sprint 4 (pilot readiness):
- 5,000 flights / multi-day / 5-event closure < 10 seconds wall clock
  on a developer-class machine. The threshold is intentionally generous
  to avoid flakiness on shared CI runners.

The fixture is generated programmatically (no Excel I/O) so that this
test is hermetic and does not bloat the repo with a 5k-row spreadsheet.
"""

from __future__ import annotations

import time as _time
from datetime import date, time, timedelta

import pandas as pd
import pytest

from src.cascade.cascade_detector import compute_kpis, detect_cascade_multi
from src.models.event import AirportClosureEvent

PERF_THRESHOLD_SECONDS = 10.0


def _build_large_fleet(num_flights: int = 5000, days: int = 3) -> pd.DataFrame:
    """Return a synthetic flight schedule with realistic rotation patterns.

    250 tails × ~6 sectors/day across ``days`` days produces ~``num_flights``
    rows. Each tail ping-pongs between HAN and a rotating set of stations
    so that the cascade detector has plenty of downstream chains to walk.
    """
    stations = ["HAN", "SGN", "DAD", "CXR", "PXU", "HPH", "VII", "BMV", "VCS", "PQC"]
    base_date = date(2026, 4, 24)
    rows: list[dict[str, object]] = []
    flt_seq = 1000
    sectors_per_day = max(1, num_flights // (250 * days))
    for tail_idx in range(250):
        reg = f"VN-A{tail_idx:03d}"
        ac_type = "A321" if tail_idx % 2 else "A350"
        for d in range(days):
            current_loc = "HAN" if tail_idx % 2 == 0 else stations[(tail_idx + d) % len(stations)]
            departure_minute = 6 * 60 + (tail_idx * 17) % 60  # spread across morning
            for s in range(sectors_per_day):
                next_loc = stations[(tail_idx + s + d) % len(stations)]
                if next_loc == current_loc:
                    next_loc = stations[(tail_idx + s + d + 1) % len(stations)]
                std_total = (departure_minute + s * 150) % (24 * 60)
                sta_total = (std_total + 90) % (24 * 60)
                std = time(std_total // 60, std_total % 60)
                sta = time(sta_total // 60, sta_total % 60)
                rows.append(
                    {
                        "flight_date": base_date + timedelta(days=d),
                        "flight_no": str(flt_seq),
                        "aircraft_reg": reg,
                        "aircraft_type": ac_type,
                        "origin": current_loc,
                        "destination": next_loc,
                        "std": std,
                        "sta": sta,
                        "raw_row_number": flt_seq,
                    }
                )
                flt_seq += 1
                current_loc = next_loc
                if len(rows) >= num_flights:
                    return pd.DataFrame(rows)
    return pd.DataFrame(rows)


@pytest.mark.performance
def test_cascade_5000_flights_5_events_under_10_seconds() -> None:
    """5k flights × 5 simultaneous closures must finish under threshold.

    This protects against accidental O(n²) regressions when we add more
    per-row work to the cascade detector (Sprint 4 added the
    ``impact_explanation`` column, Sprint 7 will add recovery scoring).
    """
    df = _build_large_fleet(num_flights=5000, days=3)
    assert len(df) >= 4500, f"fixture too small: {len(df)}"

    events = [
        AirportClosureEvent(
            airport=ap,
            closure_date=date(2026, 4, 24),
            start_time=time(14, 0),
            end_time=time(18, 0),
            closure_type="airport_closed",
        )
        for ap in ("HAN", "SGN", "DAD", "CXR", "HPH")
    ]

    started = _time.perf_counter()
    result = detect_cascade_multi(df, events)
    elapsed = _time.perf_counter() - started

    kpis = compute_kpis(result)
    assert kpis["total_flights"] == len(df)
    assert kpis["affected_flights"] > 0, "expected non-trivial cascade impact"
    assert elapsed < PERF_THRESHOLD_SECONDS, (
        f"cascade detection took {elapsed:.2f}s, threshold {PERF_THRESHOLD_SECONDS}s"
    )
