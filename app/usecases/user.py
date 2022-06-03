from __future__ import annotations

import time

import orjson

import app.state
from app.constants.mode import Mode
from app.constants.privileges import Privileges
from app.objects.user import User


async def update_status(user: User) -> None:
    await app.state.services.redis.publish(
        "user-status",
        orjson.dumps(
            {
                "id": user.id,
                "status": user.status.__dict__,
            },
        ),
    )


async def update_activity(user: User) -> None:
    latest = int(time.time())

    user_collection = app.state.services.database.users
    await user_collection.update_one(
        {"id": user.id},
        {"$set": {"latest_activity": latest}},
    )

    await app.state.services.redis.publish(
        "user-activity",
        orjson.dumps(
            {
                "id": user.id,
                "activity": latest,
            },
        ),
    )


async def set_privileges(user: User, privileges: Privileges) -> None:
    user.privileges = privileges

    user_collection = app.state.services.database.users
    await user_collection.update_one(
        {"id": user.id},
        {"$set": {"privileges": privileges}},
    )

    await app.state.services.redis.publish(
        "user-privileges",
        orjson.dumps({"id": user.id, "privileges": privileges.value}),
    )


async def add_privilege(user: User, privilege: Privileges) -> None:
    await set_privileges(user, user.privileges | privilege)


BOT_USERNAME = None


async def restrict(user: User, reason: str) -> None:
    if BOT_USERNAME is None:
        user_collection = app.state.services.users
        bot_user = await user_collection.find_one({"id": 1})

        BOT_USERNAME = bot_user["name"]

    logs_collection = app.state.services.database.logs
    await logs_collection.update_one(
        {"id": user.id},
        {
            "$addToSet": {
                "actions": {
                    "action": "restrict",
                    "sender": BOT_USERNAME,
                    "info": reason,
                },
            },
        },
    )

    await add_privilege(user, Privileges.RESTRICTED)
