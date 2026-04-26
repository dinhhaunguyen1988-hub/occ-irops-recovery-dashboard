"""Rule-based recovery option generation per Level-1 flight.

The engine emits the *standard* set of recovery options every L1
flight has on the table:

- **delay**: hold the flight until ``end_time + buffer``.
- **swap_tail**: pull a free aircraft (registered tail not in the
  current rotation chain) and operate the flight on it.
- **cancel**: cancel the flight outright.

Each option is scored by:

- Pax disrupted (lower is better).
- Cost USD (lower is better).
- Operational simplicity (a delay typically beats a swap, which
  typically beats a cancel).

The score formula is intentionally trivial and transparent (linear
combination of 3 normalised terms) so DMs can reason about why an
option is ranked where it is. Sprint 8+ can layer crew legality,
slot constraints, and ML-driven re-ranking on top.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

import pandas as pd

# Operational-simplicity penalty per option type. Lower = simpler.
_OP_PENALTY = {
    "delay": 0.0,
    "swap_tail": 1.0,
    "cancel": 3.0,
}

# Default penalty weights. Caller can override via ``score_options``.
DEFAULT_WEIGHTS: dict[str, float] = {
    "pax": 1.0,
    "cost": 0.5,
    "op": 100.0,
}


@dataclass
class RecoveryOption:
    """A single recovery suggestion for a Level-1 flight."""

    flight_no: str
    aircraft_reg: str | None
    option: str  # "delay" | "swap_tail" | "cancel"
    description: str
    pax_affected: int
    cost_usd: float
    score: float = 0.0
    # Optional, populated for swap_tail to identify the candidate aircraft.
    swap_candidate_reg: str | None = None
    extra: dict[str, Any] = field(default_factory=dict)


def _delay_minutes_after_window(closure_end_minutes: int) -> int:
    """How many minutes a delayed flight is pushed past the window end."""
    # 30-min taxi/turnaround buffer is the conservative default.
    return 30


def _free_tails(df: pd.DataFrame) -> list[str]:
    """Return aircraft registrations that aren't in any affected rotation.

    A tail is "free" if it has *no* flights in the affected set across
    the day. This is a coarse proxy — production deployments will
    refine it with maintenance / standby data — but it's a useful
    candidate set.
    """
    if df.empty or "aircraft_reg" not in df.columns:
        return []
    affected_tails = set(
        df.loc[df["impact_level_numeric"].notna(), "aircraft_reg"].dropna().astype(str)
    )
    all_tails = set(df["aircraft_reg"].dropna().astype(str))
    return sorted(all_tails - affected_tails)


def suggest_recovery_options(
    df_result: pd.DataFrame,
    closure_end_minutes: int = 18 * 60,
    weights: dict[str, float] | None = None,
) -> list[RecoveryOption]:
    """Generate ranked recovery options for every Level-1 flight.

    Parameters
    ----------
    df_result : pd.DataFrame
        Output of ``detect_cascade_multi`` (must contain
        ``impact_level_numeric``, ``flight_no``, ``aircraft_reg``,
        and ``est_pax`` / ``est_cost_usd``).
    closure_end_minutes : int
        End of the closure window in minutes-since-midnight (used only
        to format the delay description).
    weights : dict, optional
        Override scoring weights. Keys: ``pax``, ``cost``, ``op``.

    Returns
    -------
    list[RecoveryOption]
        Sorted ascending by score (lowest = best recommendation).
    """
    if df_result.empty:
        return []

    weights = {**DEFAULT_WEIGHTS, **(weights or {})}
    free_tails = _free_tails(df_result)

    options: list[RecoveryOption] = []
    l1 = df_result[df_result["impact_level_numeric"] == 1]
    if l1.empty:
        return []

    delay_buffer = _delay_minutes_after_window(closure_end_minutes)
    closure_end_h, closure_end_m = divmod(closure_end_minutes, 60)
    delay_end_total = closure_end_minutes + delay_buffer
    delay_end_h, delay_end_m = divmod(delay_end_total % (24 * 60), 60)
    description_window = (
        f"{closure_end_h:02d}:{closure_end_m:02d} → {delay_end_h:02d}:{delay_end_m:02d}"
    )

    for _, row in l1.iterrows():
        flight_no = str(row.get("flight_no", "?"))
        reg = row.get("aircraft_reg")
        reg_str = str(reg) if pd.notna(reg) else None
        pax = int(row.get("est_pax", 0) or 0)
        cost = float(row.get("est_cost_usd", 0) or 0.0)

        # Delay
        options.append(
            RecoveryOption(
                flight_no=flight_no,
                aircraft_reg=reg_str,
                option="delay",
                description=(
                    f"Delay until window clears + {delay_buffer}min taxi buffer "
                    f"({description_window})"
                ),
                pax_affected=pax,
                cost_usd=cost,
            )
        )

        # Swap (only if there's a candidate tail). Swapping eliminates
        # the cascade for this leg, so cost is ~0 modulo turnaround.
        if free_tails:
            swap_target = free_tails[0]
            options.append(
                RecoveryOption(
                    flight_no=flight_no,
                    aircraft_reg=reg_str,
                    option="swap_tail",
                    description=(
                        f"Swap to free tail {swap_target}; original flight operates near-on-time"
                    ),
                    pax_affected=0,
                    cost_usd=cost * 0.1,  # ~10% residual cost
                    swap_candidate_reg=swap_target,
                )
            )

        # Cancel
        options.append(
            RecoveryOption(
                flight_no=flight_no,
                aircraft_reg=reg_str,
                option="cancel",
                description=("Cancel flight; pax reaccommodated via downstream rotation"),
                pax_affected=pax,
                cost_usd=cost * 1.5,  # cancellation is more expensive than delay
            )
        )

    return score_options(options, weights=weights)


def score_options(
    options: list[RecoveryOption],
    weights: dict[str, float] | None = None,
) -> list[RecoveryOption]:
    """Compute ``score`` on each option and return them sorted ascending.

    Score = ``w_pax × pax + w_cost × cost + w_op × op_penalty``.
    Lower is better. The function mutates each option's ``score``
    field in place AND returns the sorted list, so callers don't need
    to remember which.
    """
    weights = {**DEFAULT_WEIGHTS, **(weights or {})}

    for opt in options:
        opt.score = (
            weights["pax"] * opt.pax_affected
            + weights["cost"] * opt.cost_usd
            + weights["op"] * _OP_PENALTY.get(opt.option, 0.0)
        )

    return sorted(options, key=lambda o: (o.flight_no, o.score))
