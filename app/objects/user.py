from __future__ import annotations

from dataclasses import dataclass

import app.config
import app.state
from app.constants.privileges import Privileges
from app.constants.status import Status
from app.objects.geolocation import Geolocation


@dataclass
class User:
    id: int
    name: str
    status: Status
    login_time: int
    latest_activity: int
    geolocation: Geolocation
    privileges: Privileges
    friends: list[int]

    def __repr__(self) -> str:
        return f"<{self.name} ({self.id})>"

    @property
    def url(self) -> str:
        return f"https://{app.config.SERVER_DOMAIN}/u/{self.id}"

    @property
    def embed(self) -> str:
        return f"[{self.url} {self.name}]"
