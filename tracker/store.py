"""Persistent market tracker: daily snapshots + rolling per-vehicle history.

- data/snapshots/YYYY-MM-DD.json  full normalized pull for that day
- data/history.json               per-VIN record: first/last seen, price history,
                                  lowest price ever, currently-listed flag

These JSON files are committed back to the repo by the GitHub Action, so the
price history accrues over time and stays diff-friendly.
"""
from __future__ import annotations

import json
from pathlib import Path
from statistics import median
from typing import Any

import config
from tracker.models import Listing


def _read_json(path: Path, default: Any) -> Any:
    if not path.exists():
        return default
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return default


def _write_json(path: Path, obj: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(obj, indent=2, sort_keys=True), encoding="utf-8")


def save_snapshot(listings: list[Listing], today: str) -> Path:
    path = config.SNAPSHOT_DIR / f"{today}.json"
    _write_json(path, [l.to_dict() for l in listings])
    return path


def update_history(listings: list[Listing], today: str) -> dict[str, Any]:
    """Update the rolling history and return a diff for today's report."""
    history: dict[str, Any] = _read_json(config.HISTORY_FILE, {})
    seen: set[str] = set()
    new_listings: list[Listing] = []
    price_drops: list[dict[str, Any]] = []

    for l in listings:
        seen.add(l.key)
        rec = history.get(l.key)
        if rec is None:
            history[l.key] = {
                "key": l.key, "vin": l.vin, "title": l.title, "url": l.url,
                "first_seen": today, "last_seen": today,
                "first_price": l.price, "last_price": l.price, "lowest_price": l.price,
                "price_history": [{"date": today, "price": l.price}],
                "currently_listed": True,
            }
            new_listings.append(l)
        else:
            prev = rec.get("last_price")
            if l.price is not None and prev is not None and l.price < prev:
                price_drops.append({"listing": l, "old": prev, "new": l.price})
            ph = rec.setdefault("price_history", [])
            if not ph or ph[-1].get("price") != l.price:
                ph.append({"date": today, "price": l.price})
            rec["last_seen"] = today
            rec["last_price"] = l.price
            rec["url"] = l.url or rec.get("url", "")
            rec["title"] = rec.get("title") or l.title
            if l.price is not None:
                lp = rec.get("lowest_price")
                rec["lowest_price"] = l.price if lp is None else min(lp, l.price)
            rec["currently_listed"] = True

    # Vehicles present in the previous run but missing now = sold/removed.
    newly_gone: list[dict[str, Any]] = []
    for k, rec in history.items():
        if k not in seen:
            if rec.get("currently_listed"):
                newly_gone.append(rec)
            rec["currently_listed"] = False

    _write_json(config.HISTORY_FILE, history)
    return {
        "new": new_listings,
        "price_drops": sorted(price_drops, key=lambda d: d["old"] - d["new"], reverse=True),
        "newly_gone": newly_gone,
        "available_now": len(seen),
        "total_tracked": len(history),
    }


def market_summary(listings: list[Listing]) -> dict[str, Any]:
    prices = sorted(l.price for l in listings if l.price)
    miles = [l.miles for l in listings if l.miles]
    return {
        "count": len(listings),
        "median_price": int(median(prices)) if prices else None,
        "min_price": prices[0] if prices else None,
        "max_price": prices[-1] if prices else None,
        "avg_miles": int(sum(miles) / len(miles)) if miles else None,
    }
