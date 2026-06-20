"""Auto.dev Vehicle Listings API source (optional alternative/fallback).

Docs: https://docs.auto.dev/v2/products/vehicle-listings
Endpoint: GET https://api.auto.dev/listings  (Authorization: Bearer <key>)

Auto.dev's exact response field names vary by plan and are less documented than
Marketcheck's, so the mapping below tries several likely paths for each field.
If you adopt this source as primary, run once with --dry-run and adjust the
paths in `_map` to match the JSON you actually get back.
"""
from __future__ import annotations

import requests

import config
from tracker.models import Listing
from tracker.sources.base import Source
from tracker.util import dig, title_status_clean, to_float, to_int

API_URL = "https://api.auto.dev/listings"


class AutodevSource(Source):
    name = "autodev"

    def __init__(self, api_key: str):
        if not api_key:
            raise ValueError("AUTODEV_API_KEY is not set")
        self.api_key = api_key
        self.session = requests.Session()
        self.session.headers.update({"Authorization": f"Bearer {api_key}"})

    def _map(self, item: dict) -> Listing:
        return Listing(
            source=self.name,
            listing_id=str(item.get("id", "") or dig(item, "vehicle.vin", default="")),
            vin=str(dig(item, "vehicle.vin", "vin", default="")),
            year=to_int(dig(item, "vehicle.year", "year")),
            make=str(dig(item, "vehicle.make", "make", default=config.MAKE)),
            model=str(dig(item, "vehicle.model", "model", default=config.MODEL)),
            trim=str(dig(item, "vehicle.trim", "trim", default="")),
            price=to_int(dig(item, "retailListing.price", "price")),
            miles=to_int(dig(item, "vehicle.mileage", "miles", "mileage")),
            title_clean=title_status_clean(dig(item, "vehicle.titleStatus", "titleStatus")),
            dist_miles=to_float(dig(item, "distance", "dist")),
            dealer_name=str(dig(item, "dealer.name", "dealerName", default="")),
            dealer_city=str(dig(item, "location.city", "city", default="")),
            dealer_state=str(dig(item, "location.state", "state", default="")),
            dealer_zip=str(dig(item, "location.zip", "zip", default="")),
            url=str(dig(item, "clickoffUrl", "vdpUrl", "detailUrl", "url", default="")),
            photo=str(dig(item, "primaryPhotoUrl", "photoUrl", default="")),
            comments=str(dig(item, "sellerComments", "description", default="")),
        )

    def fetch(self) -> list[Listing]:
        out: dict[str, Listing] = {}
        page = 1
        while len(out) < config.MAX_LISTINGS:
            params = {
                "vehicle.make": config.MAKE,
                "vehicle.model": config.MODEL,
                "retailListing.price": f"0-{config.PRICE_MAX}",
                "zip": config.HOME_ZIP,
                "distance": config.SEARCH_RADIUS_MILES,
                "page": page,
                "limit": 100,
                "sort": "price.asc",
            }
            resp = self.session.get(API_URL, params=params, timeout=30)
            if resp.status_code == 401:
                raise RuntimeError("Auto.dev rejected the API key (401). Check AUTODEV_API_KEY.")
            resp.raise_for_status()
            data = resp.json()
            records = (data.get("records") or data.get("listings")
                       or data.get("data") or [])
            if not records:
                break
            for item in records:
                lst = self._map(item)
                out[lst.key] = lst
            if len(records) < 100:
                break
            page += 1
        return list(out.values())
