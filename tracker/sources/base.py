"""Source interface. A source turns a provider's API into normalized Listings."""
from __future__ import annotations

from abc import ABC, abstractmethod

from tracker.models import Listing


class Source(ABC):
    name = "base"

    @abstractmethod
    def fetch(self) -> list[Listing]:
        """Return all matching listings (already de-duplicated by VIN)."""
        raise NotImplementedError
