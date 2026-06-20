"""Filtering ("mostly undamaged, better condition, <= $70k") and ranking."""
from __future__ import annotations

import config
from tracker.models import Listing


def _text_blob(l: Listing) -> str:
    return " ".join([l.title, l.trim, l.comments, l.dealer_name]).lower()


def passes(l: Listing) -> tuple[bool, str]:
    """Return (kept, reason). Reason is for logging when rejected."""
    blob = _text_blob(l)

    # Right vehicle?
    if config.MODEL.lower() not in (l.model or "").lower() and config.MODEL.lower() not in blob:
        return False, "not the target model"

    # Price ceiling.
    if l.price is None or l.price <= 0:
        return False, "no price"
    if l.price > config.PRICE_MAX:
        return False, f"over ${config.PRICE_MAX:,}"

    # Optional mileage cap.
    if config.MAX_MILES and l.miles and l.miles > config.MAX_MILES:
        return False, f"over {config.MAX_MILES:,} mi"

    # Title status. (None = unknown -> kept; explicit False -> rejected.)
    if config.REQUIRE_CLEAN_TITLE and l.title_clean is False:
        return False, "not a clean title"

    # Damage / branded keywords anywhere in the text.
    for kw in config.EXCLUDE_KEYWORDS:
        if kw in blob:
            return False, f"flagged: {kw}"

    return True, "ok"


def score(l: Listing) -> float:
    """Higher is better. Blends price, mileage, distance, plus quality bonuses."""
    def clamp01(x: float) -> float:
        return max(0.0, min(1.0, x))

    price_score = clamp01((config.PRICE_MAX - (l.price or config.PRICE_MAX)) / max(1, config.PRICE_MAX))
    if l.miles is None:
        miles_score = 0.5  # unknown mileage -> neutral
    else:
        miles_score = clamp01(1 - l.miles / max(1, config.MILES_REF))
    dist = l.dist_miles if l.dist_miles is not None else config.DISTANCE_REF
    dist_score = clamp01(1 - dist / max(1, config.DISTANCE_REF))

    s = (config.WEIGHT_PRICE * price_score
         + config.WEIGHT_MILES * miles_score
         + config.WEIGHT_DISTANCE * dist_score)

    if l.title_clean is True:
        s += 0.15
    if l.certified:
        s += 0.12
    if l.one_owner is True:
        s += 0.08
    return round(s, 4)


def filter_and_rank(listings: list[Listing]) -> list[Listing]:
    kept: list[Listing] = []
    for l in listings:
        ok, _reason = passes(l)
        if ok:
            l.score = score(l)
            kept.append(l)
    kept.sort(key=lambda x: x.score, reverse=True)
    return kept
