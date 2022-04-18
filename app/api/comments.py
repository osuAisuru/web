from __future__ import annotations

from typing import Literal
from typing import Optional

from fastapi import Depends
from fastapi import Form

import app.state
import app.usecases
from app.constants.privileges import Privileges
from app.objects.user import User
from app.utils import authenticate_user


async def osu_comment(
    user: User = Depends(authenticate_user(Form, "u", "p")),
    map_id: int = Form(..., alias="b"),
    set_id: int = Form(..., alias="s"),
    score_id: int = Form(..., alias="r", ge=0, le=9_223_372_036_854_775_807),
    mode_vn: int = Form(..., alias="m", ge=0, le=3),
    action: Literal["get", "post"] = Form(..., alias="a"),
    # only sent for post
    target: Optional[Literal["song", "map", "replay"]] = Form(None),
    colour: Optional[str] = Form(None, alias="f", min_length=6, max_length=6),
    start_time: Optional[int] = Form(None, alias="starttime"),
    comment: Optional[str] = Form(None, min_length=1, max_length=80),
):
    if action == "get":
        response = await get_comments(score_id, set_id, map_id)
    elif action == "post":
        if target == "song":
            target_id = set_id
        elif target == "map":
            target_id = map_id
        else:
            target_id = score_id

        if colour and not user.priv & Privileges.SUPPORTER:
            colour = None

        await add_comment(target_id, target, user.id, start_time, comment, colour)
        response = b""

    await app.usecases.user.update_activity(user)
    return response


async def add_comment(
    target_id: int,
    target_type: str,
    user_id: int,
    time: int,
    comment: str,
    colour: Optional[str],
) -> None:
    comments_collection = app.state.services.database.comments
    await comments_collection.insert_one(
        {
            "target_id": target_id,
            "target_type": target_type,
            "user_id": user_id,
            "time": time,
            "comment": comment,
            "colour": colour,
        },
    )


async def get_comments(score_id: int, set_id: int, map_id: int) -> bytes:
    comments_collection = app.state.services.database.comments
    users_collection = app.state.services.database.users

    comments = [
        document
        async for document in comments_collection.find(
            {
                "$or": [
                    {"target_type": "replay", "target_id": score_id},
                    {"target_type": "song", "target_id": set_id},
                    {"target_type": "map", "target_id": map_id},
                ],
            },
        )
    ]

    privileges = {
        document["id"]: document["privileges"]
        async for document in users_collection.find(
            {"id": {"$in": [comment["user_id"] for comment in comments]}},
        )
    }

    ret: list[str] = []

    for comment in comments:
        privileges = privileges[comment["user_id"]]

        if privileges & Privileges.NOMINATOR:
            fmt = "bat"
        elif privileges & Privileges.SUPPORTER:
            fmt = "supporter"
        else:
            fmt = ""

        if comment["colour"]:
            fmt += f"|{comment['colour']}"

        ret.append("{time}\t{target_type}\t{fmt}\t{comment}".format(fmt=fmt, **comment))

    return "\n".join(ret).encode()
