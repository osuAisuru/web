from __future__ import annotations

from dataclasses import dataclass
from typing import Any


@dataclass
class Country:
    code: int
    acronym: str


@dataclass
class Geolocation:
    long: float
    lat: float
    country: Country
    ip: str

    @classmethod
    def from_dict(cls, geolocation: dict[str, Any]) -> Geolocation:
        geolocation["country"] = Country(**geolocation["country"])
        return Geolocation(**geolocation)
