from __future__ import annotations

from typing import Literal

import orjson
from fastapi import Depends
from fastapi import Query

import app.state
import app.usecases
from app.constants.flags import ClientFlags
from app.objects.user import User
from app.utils import authenticate_user


async def last_fm(
    user: User = Depends(authenticate_user(Query, "us", "ha")),
    action: Literal["scrobble", "np"] = Query(...),
    map_id_or_ac_flag: str = Query(..., alias="b"),
):
    if map_id_or_ac_flag[0] != "a":
        # not ac flag, i don't care
        return b"-3"

    flags = ClientFlags(int(map_id_or_ac_flag[1:]))

    if flags & (ClientFlags.HQ_ASSEMBLY | ClientFlags.HQ_FILE):
        await app.usecases.user.restrict(user, f"hq!osu running (flags: {flags.value})")
        return b"-3"

    if flags & ClientFlags.REGISTRY_EDITS:
        # have used hq in the past (possibly now, we will warn them)
        await app.state.services.redis.publish(
            "user-notification",
            orjson.dumps(
                {
                    "id": user.id,
                    "message": (
                        "Hey! It seems you have used osu-relife in the past, which leaves a registry change.\n"
                        "Please re-install osu-relife and disable it to avoid any issues."
                    ),
                },
            ),
        )

        await app.state.services.redis.publish(
            "user-logout",
            orjson.dumps({"id": user.id}),
        )

        return b"-3"
