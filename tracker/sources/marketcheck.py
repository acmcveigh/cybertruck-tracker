"""Marketcheck Cars API source (primary).

Docs: https://docs.marketcheck.com/docs/api/cars/inventory/inventory-search
Endpoint: GET https://api.marketcheck.com/v2/search/car/active?api_key=...

We page through `used` and `certified` inventory within a radius of Vida, OR and
map each listing into our normalized model. Field access is defensive (via
`dig`) because Marketcheck nests some specs under a `build` object on some plans
and returns them at the top level on others.
"""
from __future__ import annotations

import time

import requests

import config
from tracker.models import Listing
from tracker.sources.base import Source
from tracker.util import as_bool, dig, first_in, to_float, to_int

API_URL = "https://api.marketcheck.com/v2/search/car/active"


class MarketcheckSource(Source):
    name = "marketcheck"

    def __init__(self, api_key: str):
        if not api_key:
            raise ValueError("MARKETCHECK_API_KEY is not set")
        self.api_key = api_key
        self.session = requests.Session()

    def _params(self, car_type: str, start: int) -> dict:
        params = {
            "api_key": self.api_key,
            "make": config.MAKE,
            "model": config.MODEL,
            "car_type": car_type,
            "price_range": f"0-{config.PRICE_MAX}",
            "zip": config.HOME_ZIP,
            "radius": config.SEARCH_RADIUS_MILES,
            "rows": 50,
            "start": start,
            "sort_by": "price",
            "sort_order": "asc",
        }
        return params

    def _map(self, item: dict, car_type: str) -> Listing:
        dealer = item.get("dealer") or {}
        comments = " ".join(
            str(dig(item, p, default="") or "")
            for p in ("seller_comments", "extra", "data.seller_comments")
        )
        certified = as_bool(item.get("is_certified")) is True or car_type == "certified"
        return Listing(
            source=self.name,
            listing_id=str(item.get("id", "")),
            vin=str(item.get("vin", "")),
            year=to_int(dig(item, "build.year", "year")),
            make=str(dig(item, "build.make", "make", default=config.MAKE)),
            model=str(dig(item, "build.model", "model", default=config.MODEL)),
            trim=str(dig(item, "build.trim", "trim", default="")),
            price=to_int(item.get("price")),
            miles=to_int(item.get("miles")),
            title_clean=as_bool(item.get("carfax_clean_title")),
            certified=certified,
            one_owner=as_bool(item.get("carfax_1_owner")),
            dist_miles=to_float(item.get("dist")),
            dealer_name=str(dealer.get("name", "")),
            dealer_city=str(dealer.get("city", "")),
            dealer_state=str(dealer.get("state", "")),
            dealer_zip=str(dealer.get("zip", "") or dealer.get("dealer_zip", "")),
            dealer_phone=str(dealer.get("phone", "")),
            url=str(item.get("vdp_url", "")),
            photo=first_in(item, "media.photo_links", "media.photo_links_cached",
                           "photo_links", "photo_links_cached"),
            dom=to_int(item.get("dom")),
            comments=comments,
        )

    def fetch(self) -> list[Listing]:
        out: dict[str, Listing] = {}
        for car_type in config.CAR_TYPES:
            start = 0
            while len(out) < config.MAX_LISTINGS:
                params = self._params(car_type, start)
                resp = self.session.get(API_URL, params=params, timeout=30)
                if resp.status_code == 401:
                    raise RuntimeError(
                        "Marketcheck rejected the API key (401). Check MARKETCHECK_API_KEY."
                    )
                if resp.status_code == 422:
                    raise RuntimeError(
                        f"Marketcheck returned 422 (invalid request). "
                        f"Check that your API key is fully activated and has search access. "
                        f"Response: {resp.text[:500]}"
                    )
                if resp.status_code == 429:
                    raise RuntimeError(
                        "Marketcheck rate limit hit (429). You may be out of free-tier calls."
                    )
                resp.raise_for_status()
                data = resp.json()
                listings = data.get("listings") or []
                if not listings:
                    break
                for item in listings:
                    lst = self._map(item, car_type)
                    out[lst.key] = lst  # de-dupe by VIN across car_types
                num_found = int(data.get("num_found") or 0)
                start += len(listings)
                if start >= num_found or len(listings) < params["rows"]:
                    break
                time.sleep(0.3)  # be polite to the API
        return list(out.values())
