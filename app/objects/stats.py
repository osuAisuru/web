from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from pydantic import BaseModel


class DBStats(BaseModel):
    total_score: int
    ranked_score: int

    accuracy: float
    pp: int

    max_combo: int
    total_hits: int

    playcount: int
    playtime: int


@dataclass
class Stats:
    total_score: int
    ranked_score: int

    accuracy: float
    pp: int

    max_combo: int
    total_hits: int

    playcount: int
    playtime: int

    global_rank: int
    country_rank: int

    def dict(self) -> dict[str, Any]:
        return {
            "total_score": self.total_score,
            "ranked_score": self.ranked_score,
            "accuracy": self.accuracy,
            "pp": self.pp,
            "max_combo": self.max_combo,
            "total_hits": self.total_hits,
            "playcount": self.playcount,
            "playtime": self.playtime,
        }
