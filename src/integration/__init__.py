"""Integration & automation primitives for Sprint 6.

Each submodule is *config-driven*: if the corresponding credentials
environment variable / config field is missing, the function logs a
warning and returns ``None`` instead of raising. That keeps the
dashboard usable even before IT provisions integration credentials,
while still exposing the full integration surface area for users who
have them.
"""

from src.integration.alerts import (
    AlertThresholds,
    evaluate_alerts,
    send_teams_alert,
)
from src.integration.briefing import (
    BriefingResult,
    build_briefing_payload,
    send_briefing_email,
)
from src.integration.watcher import (
    WatcherConfig,
    WatcherResult,
    poll_inbox_once,
)

__all__ = [
    "AlertThresholds",
    "BriefingResult",
    "WatcherConfig",
    "WatcherResult",
    "build_briefing_payload",
    "evaluate_alerts",
    "poll_inbox_once",
    "send_briefing_email",
    "send_teams_alert",
]
