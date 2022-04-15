from __future__ import annotations

import aioredis
from motor.motor_asyncio import AsyncIOMotorClient

import app.config
import app.state

client: AsyncIOMotorClient = None
database = None

redis: aioredis.Redis = aioredis.from_url(str(app.config.REDIS_DSN))
