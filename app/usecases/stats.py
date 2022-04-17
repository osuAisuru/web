from __future__ import annotations

import orjson
import pymongo

import app.state
from app.constants.mode import Mode
from app.objects.beatmap import RankedStatus
from app.objects.stats import DBStats
from app.objects.stats import Stats


async def fetch(user_id: int, country: str, mode: Mode) -> Stats:
    stats_collection = app.state.services.database.ustats
    stats = await stats_collection.find_one({"user_id": user_id, "mode": mode})

    db_stats = DBStats(**stats)

    global_rank = await app.state.services.redis.zrevrank(
        f"aisuru:leaderboard:{int(mode)}",
        user_id,
    )
    if global_rank is not None:
        global_rank += 1
    else:
        global_rank = 0

    country_rank = await app.state.services.redis.zrevrank(
        f"aisuru:leaderboard:{int(mode)}:{country}",
        user_id,
    )
    if country_rank is not None:
        country_rank += 1
    else:
        country_rank = 0

    return Stats(
        global_rank=global_rank,
        country_rank=country_rank,
        **db_stats.__dict__,
    )


async def save(stats: Stats, mode: Mode, user_id: int) -> None:
    stats_collection = app.state.services.database.ustats
    await stats_collection.update_one(
        {"user_id": user_id, "mode": mode.value},
        {"$set": stats.dict()},
    )


async def refresh_stats(mode: Mode, user_id: int) -> None:
    await app.state.services.redis.publish(
        "user-stats",
        orjson.dumps({"id": user_id, "mode": mode.value}),
    )


async def update_rank(stats: Stats, mode: Mode, user_id: int, country: str) -> None:
    leaderboard_str = f"aisuru:leaderboard:{mode.value}"
    country_leaderboard_str = f"{leaderboard_str}:{country}"

    await app.state.services.redis.zadd(leaderboard_str, {user_id: stats.pp})
    await app.state.services.redis.zadd(country_leaderboard_str, {user_id: stats.pp})

    global_rank = await app.state.services.redis.zrevrank(
        leaderboard_str,
        user_id,
    )
    if global_rank is not None:
        global_rank += 1
    else:
        global_rank = 0

    country_rank = await app.state.services.redis.zrevrank(
        country_leaderboard_str,
        user_id,
    )
    if country_rank is not None:
        country_rank += 1
    else:
        country_rank = 0

    stats.global_rank = global_rank
    stats.country_rank = country_rank


BONUS_PP_LIMIT = 25397


async def recalc(stats: Stats, mode: Mode, user_id: int) -> None:
    scores_collection = app.state.services.database.scores
    scores = [
        score
        async for score in (
            scores_collection.find(
                {
                    "user_id": user_id,
                    "mode": mode.value,
                    "status": 2,
                    "pp": {"$gt": 0},
                },
            )
            .sort("pp", pymongo.DESCENDING)
            .limit(BONUS_PP_LIMIT)
        )
    ]

    maps_collection = app.state.services.database.maps
    beatmaps = [
        beatmap["md5"]
        async for beatmap in maps_collection.find(
            {"md5": {"$in": [score["map_md5"] for score in scores]}},
        )
        if RankedStatus(beatmap["status"])
        in (RankedStatus.RANKED, RankedStatus.APPROVED)
    ]

    scores = [score for score in scores if score["map_md5"] in beatmaps]
    top_100 = scores[:100]

    weighted_pp = sum(score["pp"] * 0.95**idx for idx, score in enumerate(top_100))
    bonus_pp = 416.6667 * (1 - (0.994 ** len(scores)))
    pp = round(weighted_pp + bonus_pp)

    weighted_acc = sum(score["acc"] * 0.95**idx for idx, score in enumerate(top_100))
    bonus_acc = 100.0 / (20 * (1 - 0.95 ** len(top_100)))
    acc = (weighted_acc * bonus_acc) / 100.0

    stats.pp = pp
    stats.accuracy = acc
