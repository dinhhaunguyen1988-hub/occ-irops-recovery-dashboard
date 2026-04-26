"""Command-line entry-point for cron-driven integration tasks.

Usage examples::

    # Once-per-day briefing email
    python -m src.integration.cli briefing --recipients dm@vna.vn,ops@vna.vn

    # Periodic inbox scan (every 30 min)
    python -m src.integration.cli watch --inbox /var/lib/aims/dayrep --glob '*.xlsx'

The CLI deliberately reads SMTP / webhook config from environment
variables so secrets don't end up on argv. Missing variables degrade
gracefully (build payload, skip send).
"""

from __future__ import annotations

import argparse
import logging
import os
import sys
from pathlib import Path

from src.integration.briefing import build_briefing_payload, send_briefing_email
from src.integration.watcher import WatcherConfig, poll_inbox_once
from src.persistence import get_connection, init_db, list_recent_runs

logger = logging.getLogger("occ.integration.cli")


def _build_arg_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="src.integration.cli")
    sub = parser.add_subparsers(dest="cmd", required=True)

    p_brief = sub.add_parser("briefing", help="Build (and optionally send) a briefing email")
    p_brief.add_argument("--recipients", default=os.environ.get("OCC_BRIEFING_RECIPIENTS", ""))
    p_brief.add_argument("--limit", type=int, default=10, help="Number of recent runs to include")
    p_brief.add_argument("--send", action="store_true", help="Actually deliver via SMTP")
    p_brief.add_argument("--db", default="data/runs.db")

    p_watch = sub.add_parser("watch", help="Run the inbox watcher once")
    p_watch.add_argument("--inbox", required=True)
    p_watch.add_argument("--glob", default="*.xlsx")
    p_watch.add_argument("--db", default="data/runs.db")

    return parser


def _cmd_briefing(args: argparse.Namespace) -> int:
    conn = get_connection(args.db)
    init_db(conn)
    runs = list_recent_runs(conn, limit=args.limit)
    payload = build_briefing_payload(runs)
    print("Subject:", payload.subject)
    print()
    print(payload.text_body)

    if not args.send:
        return 0

    recipients = [r.strip() for r in (args.recipients or "").split(",") if r.strip()]
    smtp_host = os.environ.get("OCC_SMTP_HOST")
    if not smtp_host:
        logger.warning("OCC_SMTP_HOST not set; skipping send")
        return 0
    ok = send_briefing_email(
        payload,
        smtp_host=smtp_host,
        smtp_port=int(os.environ.get("OCC_SMTP_PORT", "587")),
        smtp_user=os.environ.get("OCC_SMTP_USER"),
        smtp_password=os.environ.get("OCC_SMTP_PASSWORD"),
        sender=os.environ.get("OCC_SMTP_FROM", "occ-irops@vna.vn"),
        recipients=recipients,
        use_tls=os.environ.get("OCC_SMTP_TLS", "1").strip() != "0",
    )
    return 0 if ok else 2


def _cmd_watch(args: argparse.Namespace) -> int:
    conn = get_connection(args.db)
    init_db(conn)
    config = WatcherConfig(
        inbox_dir=Path(args.inbox),
        glob=args.glob,
    )
    result = poll_inbox_once(conn, config)
    print(
        f"Processed: {len(result.files_processed)} | "
        f"Skipped: {len(result.files_skipped)} | "
        f"Errors: {len(result.errors)} | "
        f"Runs created: {len(result.runs_created)}"
    )
    for err in result.errors:
        print(f"  ERR  {err}", file=sys.stderr)
    return 0 if not result.errors else 2


def main(argv: list[str] | None = None) -> int:
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
    parser = _build_arg_parser()
    args = parser.parse_args(argv)
    if args.cmd == "briefing":
        return _cmd_briefing(args)
    if args.cmd == "watch":
        return _cmd_watch(args)
    parser.print_help()
    return 2


if __name__ == "__main__":  # pragma: no cover
    sys.exit(main())
