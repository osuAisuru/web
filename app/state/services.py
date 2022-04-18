from __future__ import annotations

import aioredis
from geoip2 import database as geoloc_database
from motor.motor_asyncio import AsyncIOMotorClient

import app.config
import app.state

client: AsyncIOMotorClient = None
database = None

redis: aioredis.Redis = aioredis.from_url(str(app.config.REDIS_DSN))
geoloc = geoloc_database.Reader("ext/geoloc.mmdb")
