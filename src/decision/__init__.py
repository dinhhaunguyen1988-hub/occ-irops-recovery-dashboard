"""Decision-support primitives for Sprint 7.

Three pure-function modules:

- ``recovery``  — generate ranked recovery options per Level-1 flight
  (delay / swap-tail / cancel), with transparent rule-based scores.
- ``reaccommodation`` — produce a passenger reaccommodation list for
  cancelled or heavily-delayed flights, ranked by impact priority.
- ``stress`` — multi-day, multi-airport network stress test that
  scales an existing closure scenario across days and airports and
  reports worst-case KPIs.

Everything here is **advisory**. The DM remains the decision-maker;
this layer just surfaces options so options aren't missed during a
fast-moving event.
"""

from src.decision.reaccommodation import (
    PaxReaccommodationRow,
    build_reaccommodation_list,
)
from src.decision.recovery import (
    RecoveryOption,
    score_options,
    suggest_recovery_options,
)
from src.decision.stress import (
    StressResult,
    StressScenario,
    run_stress_test,
)

__all__ = [
    "PaxReaccommodationRow",
    "RecoveryOption",
    "StressResult",
    "StressScenario",
    "build_reaccommodation_list",
    "run_stress_test",
    "score_options",
    "suggest_recovery_options",
]
