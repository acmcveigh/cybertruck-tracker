#!/usr/bin/env python3
"""Cybertruck market tracker — fetch, filter, track, and email daily deals.

Usage:
    python run.py                 # fetch + email (uses .env / environment)
    python run.py --dry-run       # build report, write data/last_report.html, no email
    python run.py --no-email      # fetch + update history, skip email
    python run.py --require-hour 8 --tz America/Los_Angeles
                                  # only proceed at 8 AM Pacific (used by the cron)
"""
from __future__ import annotations

import argparse
import sys
from datetime import datetime
from zoneinfo import ZoneInfo

import config
from tracker import emailer, filters, geo, store
from tracker.models import Listing


def build_source():
    if config.PROVIDER == "marketcheck":
        from tracker.sources.marketcheck import MarketcheckSource
        return MarketcheckSource(config.MARKETCHECK_API_KEY)
    if config.PROVIDER == "autodev":
        from tracker.sources.autodev import AutodevSource
        return AutodevSource(config.AUTODEV_API_KEY)
    raise SystemExit(f"Unknown PROVIDER {config.PROVIDER!r} (use 'marketcheck' or 'autodev')")


def ensure_distance(listings: list[Listing]) -> None:
    """Fill in distance for listings the API didn't measure (needs pgeocode)."""
    for l in listings:
        if l.dist_miles is None and l.dealer_zip:
            l.dist_miles = geo.distance_from_zip(l.dealer_zip)


def main() -> int:
    ap = argparse.ArgumentParser(description="Cybertruck market tracker")
    ap.add_argument("--dry-run", action="store_true",
                    help="Don't send email; write HTML to data/last_report.html")
    ap.add_argument("--no-email", action="store_true", help="Skip email entirely")
    ap.add_argument("--require-hour", type=int, default=None,
                    help="Only proceed if local hour == this value (for CI cron)")
    ap.add_argument("--tz", default="America/Los_Angeles", help="Timezone for dates / --require-hour")
    args = ap.parse_args()

    tz = ZoneInfo(args.tz)

    # Cron guard: GitHub Actions runs in UTC and ignores DST, so we fire the
    # workflow at two UTC times and let exactly one proceed at 8 AM Pacific.
    if args.require_hour is not None:
        hour = datetime.now(tz).hour
        if hour != args.require_hour:
            print(f"Skipping: local hour {hour} != required {args.require_hour} ({args.tz})")
            return 0

    today = datetime.now(tz).strftime("%Y-%m-%d")

    print(f"Fetching {config.MAKE} {config.MODEL} listings via {config.PROVIDER} ...")
    source = build_source()
    raw = source.fetch()
    print(f"  pulled {len(raw)} raw listings")

    ensure_distance(raw)
    ranked = filters.filter_and_rank(raw)
    print(f"  {len(ranked)} pass filters (<= ${config.PRICE_MAX:,}, clean/undamaged)")

    store.save_snapshot(ranked, today)
    diff = store.update_history(ranked, today)
    summary = store.market_summary(ranked)
    top = ranked[: config.TOP_N_EMAIL]

    subject = (f"⚡ Cybertruck Tracker — {len(ranked)} under ${config.PRICE_MAX // 1000}k, "
               f"{len(diff['new'])} new, {len(diff['price_drops'])} price drops ({today})")
    html = emailer.build_html(top, diff, summary, today)
    text = emailer.build_text(top, diff, summary, today)

    config.LAST_REPORT_HTML.parent.mkdir(parents=True, exist_ok=True)
    config.LAST_REPORT_HTML.write_text(html, encoding="utf-8")

    if args.no_email:
        print("  --no-email: skipped sending")
    elif args.dry_run:
        print(f"  --dry-run: wrote {config.LAST_REPORT_HTML}")
    elif not config.email_configured():
        print("  Email not configured; wrote HTML report only.")
    else:
        emailer.send_email(subject, html, text)
        print(f"  emailed {len(top)} picks to {config.EMAIL_TO}")

    return 0


if __name__ == "__main__":
    sys.exit(main())
