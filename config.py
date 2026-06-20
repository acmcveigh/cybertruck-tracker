"""Central configuration.

Everything is driven by environment variables (loaded from a local .env when
present). Secrets are NEVER hard-coded here -- in GitHub Actions they arrive as
repository secrets mapped to env vars.
"""
from __future__ import annotations

import os
from pathlib import Path

try:
    from dotenv import load_dotenv
    load_dotenv()
except Exception:  # python-dotenv optional; in CI the env is already populated
    pass


def _bool(name: str, default: bool) -> bool:
    val = os.getenv(name)
    if val is None or val.strip() == "":
        return default
    return val.strip().lower() in {"1", "true", "yes", "y", "on"}


def _int(name: str, default: int) -> int:
    val = os.getenv(name)
    if val is None or val.strip() == "":
        return default
    try:
        return int(float(val))
    except ValueError:
        return default


def _float(name: str, default: float) -> float:
    val = os.getenv(name)
    if val is None or val.strip() == "":
        return default
    try:
        return float(val)
    except ValueError:
        return default


# --- Paths ---
BASE_DIR = Path(__file__).resolve().parent
DATA_DIR = BASE_DIR / "data"
SNAPSHOT_DIR = DATA_DIR / "snapshots"
HISTORY_FILE = DATA_DIR / "history.json"
LAST_REPORT_HTML = DATA_DIR / "last_report.html"

# --- What we're hunting ---
MAKE = os.getenv("MAKE", "Tesla")
MODEL = os.getenv("MODEL", "Cybertruck")
PRICE_MAX = _int("PRICE_MAX", 70000)
MAX_MILES = _int("MAX_MILES", 0)          # 0 = no mileage cap
REQUIRE_CLEAN_TITLE = _bool("REQUIRE_CLEAN_TITLE", True)
CAR_TYPES = [t.strip() for t in os.getenv("CAR_TYPES", "used,certified,new").split(",") if t.strip()]

# Damage / branded-title keywords -> exclude the listing.
EXCLUDE_KEYWORDS = [
    "salvage", "rebuilt", "rebuild", "flood", "branded", "lemon",
    "wrecked", "wreck", "theft recovery", "hail damage", "fire damage",
    "frame damage", "parts only", "parts car", "mechanic special",
    "not running", "doesn't run", "does not run", "for parts",
]

# --- Home base: Vida, OR 97488 ---
HOME_ZIP = os.getenv("HOME_ZIP", "97488")
HOME_LAT = _float("HOME_LAT", 44.1460)
HOME_LON = _float("HOME_LON", -122.5698)
SEARCH_RADIUS_MILES = _int("SEARCH_RADIUS_MILES", 100)  # free tier capped at 100 miles

# --- Ranking weights (higher score = better deal) ---
WEIGHT_PRICE = _float("WEIGHT_PRICE", 1.0)
WEIGHT_MILES = _float("WEIGHT_MILES", 0.7)
WEIGHT_DISTANCE = _float("WEIGHT_DISTANCE", 0.6)
MILES_REF = _int("MILES_REF", 80000)        # mileage where miles_score hits 0
DISTANCE_REF = _int("DISTANCE_REF", 3000)   # distance where dist_score hits 0

# --- Email / report ---
TOP_N_EMAIL = _int("TOP_N_EMAIL", 12)
EMAIL_TO = os.getenv("EMAIL_TO", "tommcveigh@yahoo.com")
EMAIL_FROM_NAME = os.getenv("EMAIL_FROM_NAME", "Cybertruck Tracker")
GMAIL_USER = os.getenv("GMAIL_USER", "")
GMAIL_APP_PASSWORD = os.getenv("GMAIL_APP_PASSWORD", "").replace(" ", "")
SMTP_HOST = os.getenv("SMTP_HOST", "smtp.gmail.com")
SMTP_PORT = _int("SMTP_PORT", 465)

# --- Data provider ---
PROVIDER = os.getenv("PROVIDER", "marketcheck").strip().lower()
MARKETCHECK_API_KEY = os.getenv("MARKETCHECK_API_KEY", "")
AUTODEV_API_KEY = os.getenv("AUTODEV_API_KEY", "")

# Safety cap on listings pulled per run (pagination guard).
MAX_LISTINGS = _int("MAX_LISTINGS", 500)


def email_configured() -> bool:
    return bool(GMAIL_USER and GMAIL_APP_PASSWORD and EMAIL_TO)
