"""Carvana inventory source.

Carvana delivers nationwide, so distance isn't meaningful — listings from this
source get dist_miles=0 (treat as "ships to you"). The listing URL is built from
the VIN/stock number so Tom can click straight to the car.

Carvana's website does not offer a public API and their ToS restricts automated
access. This source hits the same JSON endpoint their own search page uses
(publicly accessible, no login required) for personal, non-commercial price
monitoring only.
"""
from __future__ import annotations

import time

import requests

import config
from tracker.models import Listing
from tracker.sources.base import Source
from tracker.util import dig, title_status_clean, to_float, to_int

API_URL = "https://www.carvana.com/api/v1/inventory"

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/124.0.0.0 Safari/537.36"
    ),
    "Accept": "application/json",
    "Content-Type": "application/json",
    "Referer": "https://www.carvana.com/cars/tesla",
}


def _listing_url(v: dict) -> str:
    vin = str(v.get("vin") or "")
    slug = str(v.get("seoSlug") or v.get("slug") or "")
    if slug:
        return f"https://www.carvana.com/vehicle/{slug}"
    if vin:
        year = v.get("year", "")
        make = str(v.get("make", "")).lower().replace(" ", "-")
        model = str(v.get("model", "")).lower().replace(" ", "-")
        return f"https://www.carvana.com/vehicle/{year}-{make}-{model}/{vin}"
    stock = v.get("stockNumber") or v.get("stockNum") or ""
    return f"https://www.carvana.com/vehicle/{stock}" if stock else "https://www.carvana.com"


def _photo(v: dict) -> str:
    imgs = (v.get("imageUrls") or v.get("images") or
            v.get("imageUrl") or [])
    if isinstance(imgs, list) and imgs:
        return str(imgs[0])
    if isinstance(imgs, str):
        return imgs
    return ""


def _price(v: dict) -> int | None:
    p = v.get("price")
    if isinstance(p, dict):
        return to_int(p.get("total") or p.get("listPrice"))
    return to_int(p)


class CarvanaSource(Source):
    name = "carvana"

    def __init__(self):
        self.session = requests.Session()
        self.session.headers.update(HEADERS)

    def _body(self, page: int) -> dict:
        return {
            "sortBy": "LowestPrice",
            "pagination": {"page": page, "pageSize": 20},
            "filters": {
                "makes": [config.MAKE],
                "models": [config.MODEL],
                "price": {"min": 0, "max": config.PRICE_MAX},
            },
        }

    def _map(self, v: dict) -> Listing:
        return Listing(
            source=self.name,
            listing_id=str(v.get("stockNumber") or v.get("stockNum") or v.get("vin") or ""),
            vin=str(v.get("vin") or ""),
            year=to_int(v.get("year")),
            make=str(v.get("make") or config.MAKE),
            model=str(v.get("model") or config.MODEL),
            trim=str(v.get("trim") or ""),
            price=_price(v),
            miles=to_int(v.get("mileage") or v.get("miles") or v.get("odometer")),
            title_clean=title_status_clean(v.get("titleStatus")),
            dist_miles=0.0,   # Carvana ships nationwide
            dealer_name="Carvana (ships to you)",
            dealer_city="",
            dealer_state="",
            url=_listing_url(v),
            photo=_photo(v),
            comments=str(v.get("description") or ""),
        )

    def fetch(self) -> list[Listing]:
        out: dict[str, Listing] = {}
        page = 1
        while len(out) < config.MAX_LISTINGS:
            try:
                resp = self.session.post(API_URL, json=self._body(page), timeout=30)
            except requests.RequestException as e:
                print(f"  Carvana request error: {e}")
                break

            if resp.status_code == 403:
                print("  Carvana blocked the request (403) — skipping")
                break
            if resp.status_code != 200:
                print(f"  Carvana returned {resp.status_code} — skipping")
                break

            try:
                data = resp.json()
            except Exception:
                print("  Carvana returned non-JSON — skipping")
                break

            # Response shape varies; try common paths.
            vehicles = (
                dig(data, "inventory.vehicles") or
                dig(data, "data.vehicles") or
                dig(data, "vehicles") or
                []
            )
            if not vehicles:
                print(f"  Carvana: no vehicles in response (page {page}). Keys: {list(data.keys())[:8]}")
                break

            for v in vehicles:
                lst = self._map(v)
                out[lst.key] = lst

            total = (dig(data, "inventory.totalCount") or
                     dig(data, "data.totalCount") or
                     dig(data, "totalCount") or 0)
            fetched = page * 20
            if fetched >= (total or fetched):
                break
            page += 1
            time.sleep(1.0)

        print(f"  Carvana: {len(out)} listings found")
        return list(out.values())
