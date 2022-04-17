from __future__ import annotations

import asyncio
from typing import Iterable
from typing import Iterator
from typing import TypedDict

import aioredis.client
import orjson

import app.state
import app.usecases
import log
from app.constants.privileges import Privileges
from app.objects.beatmap import Beatmap
from app.objects.leaderboard import Leaderboard
from app.typing import PubsubHandler


def register_pubsub(channel: str):
    def decorator(handler: PubsubHandler):
        app.state.PUBSUBS[channel] = handler

    return decorator


def get_leaderboards(beatmaps: Iterable[Beatmap]) -> Iterator[Leaderboard]:
    for beatmap in beatmaps:
        yield from beatmap.leaderboards.values()


class PrivilegeUpdate(TypedDict):
    id: int
    privileges: int


@register_pubsub("user-privileges")
async def handle_privileges_change(payload: str) -> None:
    data: PrivilegeUpdate = orjson.loads(payload)

    for leaderboard in get_leaderboards(app.usecases.beatmap.md5_cache.values()):
        for score in leaderboard.scores:
            if score.user_id == data["id"]:
                score.user_priv = Privileges(data["privileges"])

    log.info(f"Updated privileges for user ID {data['id']}")


class RedisMessage(TypedDict):
    channel: bytes
    data: bytes


async def loop_pubsubs(pubsub: aioredis.client.PubSub) -> None:
    while True:
        try:
            message: RedisMessage = await pubsub.get_message(
                ignore_subscribe_messages=True,
                timeout=1.0,
            )
            if message is not None:
                if handler := app.state.PUBSUBS.get(message["channel"].decode()):
                    await handler(message["data"].decode())

            await asyncio.sleep(0.01)
        except asyncio.TimeoutError:
            pass


async def initialise_pubsubs() -> None:
    pubsub = app.state.services.redis.pubsub()
    await pubsub.subscribe(*[channel for channel in app.state.PUBSUBS.keys()])

    pubsub_loop = asyncio.create_task(loop_pubsubs(pubsub))
    app.state.tasks.add(pubsub_loop)
