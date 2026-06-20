"""Normalized listing model shared across all data sources."""
from __future__ import annotations

from dataclasses import asdict, dataclass
from typing import Any, Optional


@dataclass
class Listing:
    source: str
    listing_id: str = ""
    vin: str = ""
    year: Optional[int] = None
    make: str = ""
    model: str = ""
    trim: str = ""
    price: Optional[int] = None
    miles: Optional[int] = None
    title_clean: Optional[bool] = None   # None = unknown
    certified: bool = False
    one_owner: Optional[bool] = None
    dist_miles: Optional[float] = None   # distance from Vida, OR
    dealer_name: str = ""
    dealer_city: str = ""
    dealer_state: str = ""
    dealer_zip: str = ""
    dealer_phone: str = ""
    url: str = ""                        # link to the seller's listing
    photo: str = ""
    dom: Optional[int] = None            # days on market (from provider)
    comments: str = ""                   # free text scanned for damage keywords
    score: float = 0.0

    @property
    def key(self) -> str:
        """Stable identity across days: prefer VIN, else source+id."""
        if self.vin:
            return self.vin.strip().upper()
        return f"{self.source}:{self.listing_id}"

    @property
    def title(self) -> str:
        bits = [str(self.year or "").strip(), self.make, self.model, self.trim]
        return " ".join(b for b in bits if b).strip() or "Tesla Cybertruck"

    def to_dict(self) -> dict[str, Any]:
        d = asdict(self)
        d["key"] = self.key
        d["title"] = self.title
        return d

    @classmethod
    def from_dict(cls, d: dict[str, Any]) -> "Listing":
        allowed = set(cls.__dataclass_fields__)  # type: ignore[attr-defined]
        return cls(**{k: v for k, v in d.items() if k in allowed})
