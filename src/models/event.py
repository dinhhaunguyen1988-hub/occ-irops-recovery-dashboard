"""Airport closure event model."""

from dataclasses import dataclass, field
from datetime import date, time

# Closure type taxonomy. Adding new types here is a label/colour change only —
# cascade detection logic does not branch on type. This is intentional: the
# operational impact is the same regardless of why the airport is closed.
CLOSURE_TYPES: dict[str, dict[str, str]] = {
    "airport_closed": {"label": "Airport closed", "colour": "#d62728"},
    "runway_closed": {"label": "Runway closed", "colour": "#ff7f0e"},
    "atc_flow": {"label": "ATC flow restriction", "colour": "#fec44f"},
}


@dataclass
class AirportClosureEvent:
    """Represents an airport closure event for IROPS analysis."""

    airport: str
    closure_date: date
    start_time: time
    end_time: time
    closure_type: str = field(default="airport_closed")

    def __post_init__(self) -> None:
        self.airport = self.airport.strip().upper()
        if self.start_time >= self.end_time:
            raise ValueError(
                f"Closure start time ({self.start_time}) must be before end time ({self.end_time})"
            )
        if self.closure_type not in CLOSURE_TYPES:
            allowed = ", ".join(sorted(CLOSURE_TYPES.keys()))
            raise ValueError(
                f"Unknown closure_type {self.closure_type!r}; expected one of: {allowed}"
            )

    @property
    def closure_type_label(self) -> str:
        return CLOSURE_TYPES[self.closure_type]["label"]

    @property
    def closure_type_colour(self) -> str:
        return CLOSURE_TYPES[self.closure_type]["colour"]

    def __str__(self) -> str:
        return (
            f"{self.airport} {self.closure_type_label.lower()} "
            f"on {self.closure_date} "
            f"from {self.start_time:%H:%M} to {self.end_time:%H:%M}"
        )
