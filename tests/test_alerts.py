"""Tests for the threshold alert engine."""

from __future__ import annotations

from src.integration.alerts import AlertThresholds, evaluate_alerts


def test_no_thresholds_means_no_alerts() -> None:
    kpis = {"affected_flights": 999, "level_1_count": 999}
    assert evaluate_alerts(kpis, AlertThresholds()) == []


def test_alert_fires_when_affected_above_threshold() -> None:
    kpis = {"affected_flights": 150}
    reasons = evaluate_alerts(kpis, AlertThresholds(min_affected=100))
    assert len(reasons) == 1
    assert "Affected flights" in reasons[0]
    assert "150" in reasons[0]


def test_no_alert_when_below_threshold() -> None:
    kpis = {"affected_flights": 50}
    assert evaluate_alerts(kpis, AlertThresholds(min_affected=100)) == []


def test_threshold_boundary_is_inclusive() -> None:
    kpis = {"affected_flights": 100}
    reasons = evaluate_alerts(kpis, AlertThresholds(min_affected=100))
    assert len(reasons) == 1


def test_multiple_thresholds_can_fire_simultaneously() -> None:
    kpis = {
        "affected_flights": 200,
        "level_1_count": 60,
        "total_pax_disrupted": 30000,
        "total_cost_usd": 2_500_000,
    }
    thr = AlertThresholds(
        min_affected=100,
        min_level_1=50,
        min_pax_disrupted=20000,
        min_cost_usd=1_000_000.0,
    )
    reasons = evaluate_alerts(kpis, thr)
    assert len(reasons) == 4


def test_missing_kpi_does_not_raise() -> None:
    reasons = evaluate_alerts({}, AlertThresholds(min_affected=100))
    assert reasons == []


def test_non_numeric_kpi_does_not_raise() -> None:
    reasons = evaluate_alerts({"affected_flights": "n/a"}, AlertThresholds(min_affected=10))
    assert reasons == []


def test_cost_message_is_formatted_with_thousands_separator() -> None:
    kpis = {"total_cost_usd": 1_234_567}
    reasons = evaluate_alerts(kpis, AlertThresholds(min_cost_usd=1_000_000))
    assert "1,234,567" in reasons[0]
    assert "1,000,000" in reasons[0]
