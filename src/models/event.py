"""Airport closure event model."""

from dataclasses import dataclass
from datetime import date, time


@dataclass
class AirportClosureEvent:
    """Represents an airport closure event for IROPS analysis."""

    airport: str
    closure_date: date
    start_time: time
    end_time: time

    def __post_init__(self) -> None:
        self.airport = self.airport.strip().upper()
        if self.start_time >= self.end_time:
            raise ValueError(
                f"Closure start time ({self.start_time}) must be before "
                f"end time ({self.end_time})"
            )

    def __str__(self) -> str:
        return (
            f"{self.airport} closure on {self.closure_date} "
            f"from {self.start_time:%H:%M} to {self.end_time:%H:%M}"
        )
