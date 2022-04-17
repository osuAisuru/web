from __future__ import annotations

import time
from enum import IntEnum
from urllib.parse import unquote_plus

from fastapi import Depends
from fastapi import Query

import app.state
import app.usecases
import log
from app.constants.mode import Mode
from app.constants.mods import Mods
from app.constants.privileges import Privileges
from app.objects.beatmap import RankedStatus
from app.objects.user import User
from app.utils import authenticate_user

unsubmitted: set[str] = set()
requires_update: set[str] = set()


class LeaderboardType(IntEnum):
    LOCAL = 0
    TOP = 1
    MODS = 2
    FRIENDS = 3
    COUNTRY = 4


async def get_leaderboard(
    user: User = Depends(authenticate_user(Query, "us", "ha")),
    requesting_from_editor_song_select: bool = Query(..., alias="s"),
    leaderboard_version: int = Query(..., alias="vv"),
    leaderboard_type_arg: int = Query(..., alias="v", ge=0, le=4),
    map_md5: str = Query(..., alias="c", min_length=32, max_length=32),
    map_filename: str = Query(..., alias="f"),
    mode_arg: int = Query(..., alias="m", ge=0, le=3),
    map_set_id: int = Query(..., alias="i", ge=-1, le=2_147_483_647),
    mods_arg: int = Query(..., alias="mods", ge=0, le=2_147_483_647),
    map_package_hash: str = Query(..., alias="h"),
    aqn_files_found: bool = Query(..., alias="a"),
):
    start = time.perf_counter_ns()

    if map_md5 in unsubmitted:
        return b"-1|false"
    elif map_md5 in requires_update:
        return b"1|false"

    mode = Mode.from_lb(mode_arg, mods_arg)
    mods = Mods(mods_arg)

    if mode != user.status.mode or mods != user.status.mods:
        user.status.mode = mode
        user.status.mods = mods

        await app.usecases.user.update_status(user)

    if leaderboard_version != 4:
        return b"error: pass"  # invalid lb version

    has_set_id = map_set_id > 0

    if has_set_id:
        # cache whole set
        await app.usecases.beatmap.fetch_by_set_id(map_set_id)

    beatmap = await app.usecases.beatmap.fetch_by_md5(map_md5)

    if not beatmap:
        if has_set_id and map_set_id not in app.usecases.beatmap.set_cache:
            unsubmitted.add(map_md5)
            return b"-1|false"

        filename = unquote_plus(map_filename)
        if has_set_id:
            for bmap in app.usecases.beatmap.set_cache[map_set_id]:
                if bmap.filename == filename:
                    map_exists = True
                    break
            else:
                map_exists = False
        else:
            map_collection = app.state.services.database.maps
            map_exists = (
                await map_collection.find_one({"filename": filename}) is not None
            )

        if map_exists:
            # map needs an update
            requires_update.add(map_md5)
            return b"1|false"
        else:
            unsubmitted.add(map_md5)
            return b"-1|false"

    if not beatmap.has_leaderboard:
        return f"{beatmap.status.value}|false".encode()

    beatmap_rating = await app.usecases.beatmap.get_rating(beatmap)

    response_lines: list[str] = []

    if not requesting_from_editor_song_select:
        leaderboard = await app.usecases.leaderboard.fetch(beatmap, mode)

        response_lines.append(
            beatmap.osu_string(
                score_count=len(leaderboard),
                rating=beatmap_rating,
            ),
        )

        personal_best = leaderboard.find_user_score(user.id)
        if personal_best:
            response_lines.append(
                personal_best["score"].osu_string(
                    user.name,
                    personal_best["rank"],
                ),
            )
        else:
            response_lines.append("")

        lb_type = LeaderboardType(leaderboard_type_arg)

        for idx, score in enumerate(leaderboard.scores[:250]):  # TODO: custom limit?
            if score.user_priv & Privileges.DISALLOWED and score.user_id != user.id:
                continue

            if lb_type == LeaderboardType.MODS and score.mods != mods:
                continue

            if (
                lb_type == LeaderboardType.COUNTRY
                and score.user_country != user.geolocation.country.acronym
            ):
                continue

            if lb_type == LeaderboardType.FRIENDS and score.user_id not in user.friends:
                continue

            # TODO: username including clan stuff
            if score.user_id == user.id:
                displayed_name = user.name
            else:
                displayed_name = score.username

            response_lines.append(score.osu_string(displayed_name, rank=idx + 1))
    else:
        response_lines.append(
            beatmap.osu_string(
                score_count=0,
                rating=beatmap_rating,
            ),
        )

    end = time.perf_counter_ns()
    formatted_time = log.format_time(end - start)
    log.info(
        f"Served {user.name} leaderboard for {beatmap.full_name} in {formatted_time}",
    )

    return "\n".join(response_lines).encode()
