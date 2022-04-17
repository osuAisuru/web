from __future__ import annotations

from fastapi import Depends
from fastapi import Query

import app.state
from app.objects.user import User
from app.utils import authenticate_user


async def get_favourites(
    user: User = Depends(authenticate_user(Query, "u", "h")),
):
    favourites_collection = app.state.services.database.favourites
    documents = favourites_collection.find({"user_id": user.id})

    return "\n".join([str(document["set_id"]) async for document in documents]).encode()


async def add_favourite(
    user: User = Depends(authenticate_user(Query, "u", "h")),
    set_id: int = Query(..., alias="a"),
):
    favourites_collection = app.state.services.database.favourites
    if await favourites_collection.find_one({"user_id": user.id, "set_id": set_id}):
        return b"You've already favourited this beatmap!"

    await favourites_collection.insert_one({"user_id": user.id, "set_id": set_id})
