from __future__ import annotations

from starlette.config import Config
from starlette.datastructures import Secret

cfg = Config(".env")

MONGODB_DSN: Secret = cfg("MONGODB_DSN", cast=Secret)
REDIS_DSN: Secret = cfg("REDIS_DSN", cast=Secret)

SERVER_DOMAIN: str = cfg("SERVER_DOMAIN")
SERVER_PORT: int = cfg("SERVER_PORT", cast=int)

DEBUG: bool = cfg("DEBUG", cast=bool)

API_SECRET: Secret = cfg("API_SECRET", cast=Secret)

OSU_API_KEY: Secret = cfg("OSU_API_KEY", cast=Secret)

MIRROR_URL: str = cfg("MIRROR_URL")

# do NOT change
VERSION = "0.1.0"
