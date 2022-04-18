from __future__ import annotations

from typing import Optional

from fastapi import Depends
from fastapi import Query

import app.state
import app.usecases
from app.objects.beatmap import RankedStatus
from app.objects.user import User
from app.utils import authenticate_user


async def osu_rate(
    user: User = Depends(authenticate_user(Query, "u", "p", error_text=b"auth fail")),
    map_md5: str = Query(..., alias="c", min_length=32, max_length=32),
    rating: Optional[int] = Query(None, alias="v", ge=1, le=10),
):
    ratings_collection = app.state.services.database.ratings
    beatmap = None

    if rating is None:
        beatmap = await app.usecases.beatmap.fetch_by_md5(map_md5)
        if not beatmap:
            return b"no exist"

        if beatmap.status > RankedStatus.RANKED:
            return b"not ranked"

        previous_rating = await ratings_collection.find_one(
            {"map_md5": map_md5, "user_id": user.id},
        )
        if not previous_rating:
            return b"ok"
    else:
        await ratings_collection.insert_one(
            {"user_id": user.id, "map_md5": map_md5, "rating": int(rating)},
        )

    ratings = [
        document["rating"]
        async for document in ratings_collection.find({"map_md5": map_md5})
    ]

    avg = sum(ratings) / len(ratings)

    if not beatmap:
        beatmap = await app.usecases.beatmap.fetch_by_md5(map_md5)

    if beatmap:
        beatmap.rating = avg

    return f"alreadyvoted\n{avg}".encode()
