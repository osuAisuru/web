from __future__ import annotations

import app.state
from app.constants.mode import Mode
from app.objects.beatmap import Beatmap
from app.objects.leaderboard import Leaderboard
from app.objects.score import Score


async def create(beatmap: Beatmap, mode: Mode) -> Leaderboard:
    leaderboard = Leaderboard(mode)

    scores_collection = app.state.services.database.scores
    scores = [
        score
        async for score in scores_collection.find(
            {
                "map_md5": beatmap.md5,
                "status": 2,
                "mode": mode.value,
            },
        )
    ]

    users_collection = app.state.services.database.users
    users = {
        user["id"]: user
        async for user in users_collection.find(
            {"id": {"$in": [score["user_id"] for score in scores]}},
        )
    }

    for score in scores:
        user = users[score["user_id"]]

        score["user_priv"] = user["privileges"]
        score["user_country"] = user["country"]
        score["username"] = user["name"]

        score_obj = await Score.from_row(score)
        leaderboard.scores.append(score_obj)

    leaderboard.sort()
    return leaderboard


async def fetch(beatmap: Beatmap, mode: Mode) -> Leaderboard:
    if leaderboard := beatmap.leaderboards.get(mode):
        return leaderboard

    leaderboard = await create(beatmap, mode)
    beatmap.leaderboards[mode] = leaderboard

    return leaderboard
