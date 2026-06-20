"""Distance-from-Vida helpers.

Marketcheck already returns `dist` (miles from the lat/long we search with), so
this is mostly a fallback for listings that arrive without a distance. The
optional `pgeocode` package gives offline ZIP -> lat/long with no API key; if it
isn't installed we just skip the fallback.
"""
from __future__ import annotations

import math
from typing import Optional

import config

try:
    import pgeocode  # type: ignore
    _NOMI = pgeocode.Nominatim("us")
except Exception:  # pragma: no cover - optional dependency
    _NOMI = None


def _home_coords() -> tuple[float, float]:
    """Vida, OR. Prefer env coords; refine from ZIP via pgeocode when present."""
    if _NOMI is not None and config.HOME_ZIP:
        try:
            rec = _NOMI.query_postal_code(config.HOME_ZIP)
            lat, lon = float(rec.latitude), float(rec.longitude)
            if not (math.isnan(lat) or math.isnan(lon)):
                return lat, lon
        except Exception:
            pass
    return config.HOME_LAT, config.HOME_LON


HOME_LAT, HOME_LON = _home_coords()


def haversine_miles(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    r = 3958.7613  # earth radius in miles
    p1, p2 = math.radians(lat1), math.radians(lat2)
    dphi = math.radians(lat2 - lat1)
    dlmb = math.radians(lon2 - lon1)
    a = math.sin(dphi / 2) ** 2 + math.cos(p1) * math.cos(p2) * math.sin(dlmb / 2) ** 2
    return 2 * r * math.asin(min(1.0, math.sqrt(a)))


def distance_from_zip(zip_code: str) -> Optional[float]:
    if not zip_code or _NOMI is None:
        return None
    try:
        rec = _NOMI.query_postal_code(str(zip_code).split("-")[0].strip())
        lat, lon = float(rec.latitude), float(rec.longitude)
        if math.isnan(lat) or math.isnan(lon):
            return None
        return round(haversine_miles(HOME_LAT, HOME_LON, lat, lon), 1)
    except Exception:
        return None
