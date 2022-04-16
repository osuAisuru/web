from __future__ import annotations

from dataclasses import dataclass

import orjson

import app.state
from app.constants.status import Status


@dataclass
class User:
    id: int
    name: str
    status: Status
    login_time: int
    latest_activity: int

    async def update_status(self) -> None:
        await app.state.services.redis.publish(
            "user-status",
            orjson.dumps(
                {
                    "id": self.id,
                    "status": self.status.__dict__,
                },
            ),
        )
