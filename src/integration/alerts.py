"""Threshold-based alerting (Teams / generic webhook).

Evaluates a KPI snapshot against configurable thresholds and emits a
short, structured payload to a webhook URL. Failure to reach the
webhook is logged but never raised — alerts are advisory, never on
the critical path of running an analysis.
"""

from __future__ import annotations

import json
import logging
import urllib.error
import urllib.request
from dataclasses import dataclass
from typing import Any

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class AlertThresholds:
    """Thresholds above which an alert fires.

    Each field is optional — leaving any field as ``None`` disables
    that particular trigger. ``min_*`` semantics: alert when the KPI
    is *greater than or equal to* the threshold.
    """

    min_affected: int | None = None
    min_level_1: int | None = None
    min_pax_disrupted: int | None = None
    min_cost_usd: float | None = None


def evaluate_alerts(
    kpis: dict[str, Any],
    thresholds: AlertThresholds,
) -> list[str]:
    """Return a list of human-readable alert reasons (empty if all clear)."""
    reasons: list[str] = []

    def _ge(kpi_key: str, threshold: float | int | None, label: str, fmt: str) -> None:
        if threshold is None:
            return
        v = kpis.get(kpi_key)
        if v is None:
            return
        try:
            if float(v) >= float(threshold):
                reasons.append(fmt.format(label=label, value=v, threshold=threshold))
        except (TypeError, ValueError):
            return

    _ge(
        "affected_flights",
        thresholds.min_affected,
        "Affected flights",
        "{label} = {value} ≥ {threshold}",
    )
    _ge(
        "level_1_count",
        thresholds.min_level_1,
        "Level 1 flights",
        "{label} = {value} ≥ {threshold}",
    )
    _ge(
        "total_pax_disrupted",
        thresholds.min_pax_disrupted,
        "Pax disrupted",
        "{label} = {value} ≥ {threshold}",
    )
    _ge(
        "total_cost_usd",
        thresholds.min_cost_usd,
        "Cost impact (USD)",
        "{label} = {value:,.0f} ≥ {threshold:,.0f}",
    )

    return reasons


def _build_teams_card(title: str, reasons: list[str], kpis: dict[str, Any]) -> dict:
    """Build a minimal Teams MessageCard payload (works with O365 webhooks)."""
    facts = [{"name": k, "value": str(v)} for k, v in kpis.items() if isinstance(v, (int, float))]
    return {
        "@type": "MessageCard",
        "@context": "https://schema.org/extensions",
        "summary": title,
        "title": title,
        "themeColor": "EE4B2B",
        "sections": [
            {
                "text": "**Triggered:** " + "; ".join(reasons),
                "facts": facts[:12],
            }
        ],
    }


def send_teams_alert(
    webhook_url: str,
    title: str,
    reasons: list[str],
    kpis: dict[str, Any],
    timeout: float = 5.0,
) -> bool:
    """Post an alert card to ``webhook_url``. Returns success/failure.

    Errors are caught and logged; the function never raises. This
    keeps the analysis-completion code path bulletproof even if the
    IT-provisioned webhook URL is wrong or temporarily unreachable.
    """
    if not webhook_url:
        logger.info("teams_alert_skipped_no_webhook")
        return False
    payload = _build_teams_card(title, reasons, kpis)
    body = json.dumps(payload).encode("utf-8")
    req = urllib.request.Request(
        webhook_url,
        data=body,
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:  # noqa: S310
            ok = 200 <= resp.status < 300
            logger.info("teams_alert_sent", extra={"status": resp.status})
            return ok
    except (urllib.error.URLError, TimeoutError) as exc:
        logger.warning("teams_alert_failed", extra={"error": str(exc)})
        return False
