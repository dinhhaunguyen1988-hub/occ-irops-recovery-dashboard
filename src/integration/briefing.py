"""Scheduled briefing assembly + optional SMTP delivery.

Designed to be called from a cron job (``python -m src.integration.cli
briefing --send``) so a morning briefing email lands in the DM inbox
before shift handover. The function is split into a *build* phase (no
network) and an optional *send* phase (SMTP) so either can be used
independently.
"""

from __future__ import annotations

import logging
import smtplib
from dataclasses import dataclass
from datetime import datetime, timezone
from email.message import EmailMessage
from typing import Any

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class BriefingResult:
    subject: str
    text_body: str
    html_body: str


def build_briefing_payload(
    runs: list[dict[str, Any]],
    title_prefix: str = "OCC IROPS Daily Briefing",
) -> BriefingResult:
    """Render a brief multi-run summary into plain-text + HTML."""
    now = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")
    if not runs:
        subject = f"{title_prefix} — {now} — no runs"
        text = (
            f"{title_prefix}\nGenerated: {now}\n\nNo cascade analysis runs in the briefing window."
        )
        html = (
            f"<h2>{title_prefix}</h2>"
            f"<p>Generated: {now}</p>"
            "<p><i>No cascade analysis runs in the briefing window.</i></p>"
        )
        return BriefingResult(subject=subject, text_body=text, html_body=html)

    lines: list[str] = [f"{title_prefix}", f"Generated: {now}", ""]
    rows: list[str] = []
    for r in runs:
        kpi = r.get("kpi_snapshot", {}) or {}
        events = ", ".join(
            f"{e.get('airport', '?')} {e.get('start_time', '')}-{e.get('end_time', '')}"
            for e in r.get("closure_config", []) or []
        )
        line = (
            f"#{r.get('id')} [{r.get('created_at', '?')}] {events} "
            f"L1={kpi.get('level_1_count', '-')} L2={kpi.get('level_2_count', '-')} "
            f"L3+={kpi.get('level_3plus_count', '-')} "
            f"Pax={kpi.get('total_pax_disrupted', '-')} "
            f"Cost=${kpi.get('total_cost_usd', '-')}"
        )
        lines.append(line)
        rows.append(
            "<tr>"
            f"<td>#{r.get('id')}</td>"
            f"<td>{r.get('created_at', '?')}</td>"
            f"<td>{events or '—'}</td>"
            f"<td>{kpi.get('level_1_count', '-')}</td>"
            f"<td>{kpi.get('level_2_count', '-')}</td>"
            f"<td>{kpi.get('level_3plus_count', '-')}</td>"
            f"<td>{kpi.get('total_pax_disrupted', '-')}</td>"
            f"<td>${kpi.get('total_cost_usd', '-')}</td>"
            "</tr>"
        )

    subject = f"{title_prefix} — {now} — {len(runs)} run(s)"
    text = "\n".join(lines)
    html = (
        f"<h2>{title_prefix}</h2>"
        f"<p>Generated: {now}</p>"
        "<table border='1' cellspacing='0' cellpadding='4'>"
        "<tr><th>Run</th><th>Time</th><th>Events</th><th>L1</th><th>L2</th>"
        "<th>L3+</th><th>Pax</th><th>Cost</th></tr>" + "".join(rows) + "</table>"
    )
    return BriefingResult(subject=subject, text_body=text, html_body=html)


def send_briefing_email(
    briefing: BriefingResult,
    *,
    smtp_host: str,
    smtp_port: int,
    smtp_user: str | None,
    smtp_password: str | None,
    sender: str,
    recipients: list[str],
    use_tls: bool = True,
) -> bool:
    """Send the briefing via SMTP. Returns True on success.

    Failures are logged and return False so the cron job exits with a
    clean status code; the operator should monitor the log.
    """
    if not recipients:
        logger.info("briefing_email_skipped_no_recipients")
        return False

    msg = EmailMessage()
    msg["Subject"] = briefing.subject
    msg["From"] = sender
    msg["To"] = ", ".join(recipients)
    msg.set_content(briefing.text_body)
    msg.add_alternative(briefing.html_body, subtype="html")

    try:
        with smtplib.SMTP(smtp_host, smtp_port, timeout=15) as server:
            if use_tls:
                server.starttls()
            if smtp_user and smtp_password:
                server.login(smtp_user, smtp_password)
            server.send_message(msg)
        logger.info("briefing_email_sent", extra={"recipients": len(recipients)})
        return True
    except (OSError, smtplib.SMTPException) as exc:
        logger.warning("briefing_email_failed", extra={"error": str(exc)})
        return False
