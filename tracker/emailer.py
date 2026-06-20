"""Builds the daily HTML/plain-text report and sends it via Gmail SMTP."""
from __future__ import annotations

import smtplib
from datetime import datetime
from email.header import Header
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from email.utils import formataddr
from html import escape
from typing import Any

import config
from tracker.models import Listing


def _money(v: Any) -> str:
    return f"${v:,}" if isinstance(v, (int, float)) else "—"


def _miles(v: Any) -> str:
    return f"{v:,} mi" if isinstance(v, (int, float)) else "— mi"


def _dist(l: Listing) -> str:
    if l.dist_miles is None:
        return "distance n/a"
    return f"{round(l.dist_miles):,} mi from Vida"


def _badges(l: Listing) -> str:
    out = []
    if l.title_clean is True:
        out.append('<span style="background:#e6f4ea;color:#137333;padding:2px 8px;'
                   'border-radius:10px;font-size:12px;">Clean title</span>')
    if l.certified:
        out.append('<span style="background:#e8f0fe;color:#1a73e8;padding:2px 8px;'
                   'border-radius:10px;font-size:12px;">Certified</span>')
    if l.one_owner is True:
        out.append('<span style="background:#fef7e0;color:#b06000;padding:2px 8px;'
                   'border-radius:10px;font-size:12px;">1 owner</span>')
    return " ".join(out)


def _card(l: Listing) -> str:
    if l.photo:
        photo = (f'<img src="{escape(l.photo, quote=True)}" alt="" width="180" '
                 'style="width:180px;max-width:180px;border-radius:8px;display:block;">')
    else:
        photo = '<div style="width:180px;height:120px;background:#f1f3f4;border-radius:8px;"></div>'
    dealer = escape(", ".join(b for b in [l.dealer_city, l.dealer_state] if b)
                    or l.dealer_name or "Dealer")
    link = ""
    if l.url:
        link = (f'<a href="{escape(l.url, quote=True)}" style="display:inline-block;'
                'background:#111;color:#fff;text-decoration:none;padding:8px 16px;'
                'border-radius:6px;font-size:14px;">View listing →</a>')
    return f"""
    <table cellpadding="0" cellspacing="0" style="width:100%;border:1px solid #e0e0e0;border-radius:10px;margin-bottom:14px;">
      <tr>
        <td style="padding:14px;vertical-align:top;width:194px;">{photo}</td>
        <td style="padding:14px 14px 14px 0;vertical-align:top;">
          <div style="font-size:17px;font-weight:700;color:#111;">{escape(l.title)}</div>
          <div style="font-size:24px;font-weight:800;color:#111;margin:4px 0;">{_money(l.price)}</div>
          <div style="font-size:14px;color:#444;margin-bottom:6px;">{_miles(l.miles)} &nbsp;&bull;&nbsp; {_dist(l)}</div>
          <div style="margin-bottom:8px;">{_badges(l)}</div>
          <div style="font-size:13px;color:#666;margin-bottom:10px;">{dealer}</div>
          {link}
        </td>
      </tr>
    </table>"""


def _stat(label: str, value: Any) -> str:
    shown = value if value is not None else "—"
    return (f'<td style="background:#f7f8f9;border-radius:8px;padding:10px 12px;text-align:center;">'
            f'<div style="font-size:20px;font-weight:800;color:#111;">{shown}</div>'
            f'<div style="font-size:11px;color:#777;text-transform:uppercase;letter-spacing:.04em;">{label}</div></td>'
            f'<td style="width:8px;"></td>')


def build_html(top: list[Listing], diff: dict, summary: dict, today: str) -> str:
    new_count = len(diff.get("new", []))
    drop_count = len(diff.get("price_drops", []))

    header = f"""
    <div style="background:#111;color:#fff;padding:18px 20px;border-radius:10px;margin-bottom:18px;">
      <div style="font-size:20px;font-weight:800;">⚡ Cybertruck Market Tracker</div>
      <div style="font-size:13px;color:#bbb;margin-top:2px;">{today} &middot; listings ≤ {_money(config.PRICE_MAX)} within {config.SEARCH_RADIUS_MILES:,} mi of Vida, OR</div>
    </div>
    <table cellpadding="0" cellspacing="0" style="width:100%;margin-bottom:20px;"><tr>
      {_stat("Available", summary.get("count"))}
      {_stat("Median price", _money(summary.get("median_price")))}
      {_stat("Cheapest", _money(summary.get("min_price")))}
      {_stat("New today", new_count)}
      {_stat("Price drops", drop_count)}
    </tr></table>"""

    picks = "".join(_card(l) for l in top) or "<p>No matching listings today.</p>"
    body = header + f'<h2 style="font-size:18px;">\U0001f525 Top picks</h2>{picks}'

    if new_count:
        body += '<h2 style="font-size:18px;margin-top:22px;">\U0001f195 New since yesterday</h2>'
        body += "".join(_card(l) for l in diff["new"][:8])

    if drop_count:
        rows = "".join(
            f'<li style="margin-bottom:6px;">{escape(d["listing"].title)} — '
            f'<s style="color:#999;">{_money(d["old"])}</s> <b>{_money(d["new"])}</b> '
            f'(<a href="{escape(d["listing"].url, quote=True)}">view</a>)</li>'
            for d in diff["price_drops"][:10]
        )
        body += f'<h2 style="font-size:18px;margin-top:22px;">\U0001f4c9 Price drops</h2><ul>{rows}</ul>'

    footer = f"""
    <div style="margin-top:24px;padding-top:14px;border-top:1px solid #e0e0e0;color:#999;font-size:12px;">
      Tracking {diff.get("total_tracked", 0)} Cybertrucks over time &middot; source: {escape(config.PROVIDER)} &middot;
      generated {datetime.now().strftime("%Y-%m-%d %H:%M")}
    </div>"""

    return ('<div style="font-family:-apple-system,Segoe UI,Roboto,Arial,sans-serif;'
            f'max-width:640px;margin:auto;color:#111;">{body}{footer}</div>')


def build_text(top: list[Listing], diff: dict, summary: dict, today: str) -> str:
    lines = [
        f"Cybertruck Market Tracker - {today}",
        f"Listings <= ${config.PRICE_MAX:,} within {config.SEARCH_RADIUS_MILES} mi of Vida, OR",
        f"Available: {summary.get('count')} | Median: {_money(summary.get('median_price'))} "
        f"| Cheapest: {_money(summary.get('min_price'))}",
        f"New today: {len(diff.get('new', []))} | Price drops: {len(diff.get('price_drops', []))}",
        "",
        "TOP PICKS:",
    ]
    for i, l in enumerate(top, 1):
        d = "n/a" if l.dist_miles is None else f"{round(l.dist_miles)} mi"
        loc = ", ".join(b for b in [l.dealer_city, l.dealer_state] if b)
        lines.append(f"{i}. {l.title} - {_money(l.price)} - {_miles(l.miles)} - {d} from Vida")
        lines.append(f"   {loc}  {l.url}")
    return "\n".join(lines)


def build_message(subject: str, html: str, text: str) -> MIMEMultipart:
    msg = MIMEMultipart("alternative")
    msg["Subject"] = Header(subject, "utf-8")            # RFC 2047 encode (handles ⚡, —)
    msg["From"] = formataddr((config.EMAIL_FROM_NAME, config.GMAIL_USER))
    msg["To"] = config.EMAIL_TO
    msg.attach(MIMEText(text, "plain", "utf-8"))
    msg.attach(MIMEText(html, "html", "utf-8"))
    return msg


def send_email(subject: str, html: str, text: str) -> None:
    if not config.email_configured():
        raise RuntimeError("Email not configured (GMAIL_USER / GMAIL_APP_PASSWORD / EMAIL_TO).")
    msg = build_message(subject, html, text)
    with smtplib.SMTP_SSL(config.SMTP_HOST, config.SMTP_PORT, timeout=30) as server:
        server.login(config.GMAIL_USER, config.GMAIL_APP_PASSWORD)
        server.sendmail(config.GMAIL_USER, [config.EMAIL_TO], msg.as_string())
