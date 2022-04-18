from __future__ import annotations

import copy
import time
from base64 import b64decode
from pathlib import Path
from typing import NamedTuple
from typing import Optional
from typing import TypeVar
from typing import Union

import orjson
from aiohttp import ClientSession
from fastapi import File
from fastapi import Form
from fastapi import Header
from fastapi import Request
from fastapi.datastructures import FormData
from py3rijndael import Pkcs7Padding
from py3rijndael import RijndaelCbc
from starlette.datastructures import UploadFile as StarletteUploadFile

import app.config
import app.state
import app.usecases
import app.utils
import log
from app.constants.mode import Mode
from app.constants.privileges import Privileges
from app.objects.beatmap import RankedStatus
from app.objects.score import Score
from app.objects.score import ScoreStatus

DATA_PATH = Path.cwd() / "data"
BEATMAPS_PATH = DATA_PATH / "beatmaps"
REPLAYS_PATH = DATA_PATH / "replays"

for path in (DATA_PATH, BEATMAPS_PATH, REPLAYS_PATH):
    if not path.exists():
        path.mkdir(parents=True)


class ScoreData(NamedTuple):
    score_data_b64: bytes
    replay_file: StarletteUploadFile


async def parse_form(score_data: FormData) -> Optional[ScoreData]:
    try:
        score_parts = score_data.getlist("score")
        assert len(score_parts) == 2, "Invalid score data"

        score_data_b64 = score_data.getlist("score")[0]
        assert isinstance(score_data_b64, str), "Invalid score data"
        replay_file = score_data.getlist("score")[1]
        assert isinstance(replay_file, StarletteUploadFile), "Invalid replay data"
    except AssertionError as exc:
        log.warning(f"Failed to validate score multipart data: ({exc.args[0]})")
        return None
    else:
        return (
            score_data_b64.encode(),
            replay_file,
        )


class ScoreClientData(NamedTuple):
    score_data: list[str]
    client_hash_decoded: str


def decrypt_score_data(
    score_data_b64: bytes,
    client_hash_b64: bytes,
    iv_b64: bytes,
    osu_version: str,
) -> tuple[list[str], str]:
    aes = RijndaelCbc(
        key=f"osu!-scoreburgr---------{osu_version}".encode(),
        iv=b64decode(iv_b64),
        padding=Pkcs7Padding(32),
        block_size=32,
    )

    score_data = aes.decrypt(b64decode(score_data_b64)).decode().split(":")
    client_hash_decoded = aes.decrypt(b64decode(client_hash_b64)).decode()

    return score_data, client_hash_decoded


import hashlib
from fastapi import status


async def check_local_file(osu_file_path: Path, map_id: int, map_md5: str) -> bool:
    if (
        not osu_file_path.exists()
        or hashlib.md5(osu_file_path.read_bytes()).hexdigest() != map_md5
    ):
        async with ClientSession() as session:
            async with session.get(f"https://old.ppy.sh/osu/{map_id}") as response:
                if response.status != status.HTTP_200_OK:
                    return False

                osu_file_path.write_bytes(await response.read())

    return True


T = TypeVar("T", bound=Union[int, float])


def chart_entry(name: str, before: Optional[T], after: T) -> str:
    return f"{name}Before:{before or ''}|{name}After:{after}"


async def submit_score(
    request: Request,
    token: str = Header(...),
    exited_out: bool = Form(..., alias="x"),
    fail_time: int = Form(..., alias="ft"),
    visual_settings_b64: bytes = Form(..., alias="fs"),
    updated_beatmap_hash: str = Form(..., alias="bmk"),
    storyboard_md5: Optional[str] = Form(None, alias="sbk"),
    iv_b64: bytes = Form(..., alias="iv"),
    unique_ids: str = Form(..., alias="c1"),
    score_time: int = Form(..., alias="st"),
    password_md5: str = Form(..., alias="pass"),
    osu_version: str = Form(..., alias="osuver"),
    client_hash_b64: bytes = Form(..., alias="s"),
    fl_cheat_screenshot: Optional[bytes] = File(None, alias="i"),
):
    start = time.perf_counter_ns()

    score_params = await parse_form(await request.form())
    if not score_params:
        return

    score_data_b64, replay_file = score_params
    score_data, client_hash_decoded = decrypt_score_data(
        score_data_b64,
        client_hash_b64,
        iv_b64,
        osu_version,
    )

    beatmap_md5 = score_data[0]
    if not (beatmap := await app.usecases.beatmap.fetch_by_md5(beatmap_md5)):
        return b"error: beatmap"

    username = score_data[1].rstrip()
    if not (user := await app.utils.get_user(username, password_md5)):
        return  # we do not depends here as we want to specifically pass an empty response if not logged in

    score = Score.from_submission(score_data[2:], beatmap_md5, user)
    leaderboard = await app.usecases.leaderboard.fetch(beatmap, score.mode)

    score.acc = app.usecases.score.calculate_accuracy(score)

    osu_file_path = BEATMAPS_PATH / f"{beatmap.id}.osu"
    if await check_local_file(osu_file_path, beatmap.id, beatmap.md5):
        if beatmap.mode.as_vn == score.mode.as_vn:
            # only get pp if the map is not a convert
            # convert support will come later
            app.usecases.performance.calculate_score(score, osu_file_path)

        if score.passed:
            old_best = leaderboard.find_user_score(user.id)

            if old_best:
                score.old_best = old_best["score"]

                if score.old_best:
                    score.old_best.rank = old_best["rank"]

            app.usecases.score.calculate_status(score)
        else:
            score.status = ScoreStatus.NOT_SUBMITTED

    await app.usecases.user.update_activity(user)

    if score.mode != user.status.mode or score.mods != user.status.mods:
        user.status.mode = score.mode
        user.status.mods = score.mods

        await app.usecases.user.update_status(user)

    score_collection = app.state.services.database.scores
    if await score_collection.find_one({"client_checksum": score.client_checksum}):
        log.warning(f"{user} submitted a duplicate score")
        return b"error: no"

    score.time_elapsed = score_time if score.passed else fail_time

    # std vn pp cap: 650
    # std rx pp cap: 1400
    # rest: None (no pp cap)

    if beatmap.gives_pp and not (
        user.privileges & Privileges.WHITELISTED
        or user.privileges & Privileges.RESTRICTED
    ):
        if score.mode == Mode.STD and score.pp >= 650:
            await app.usecases.user.restrict(
                user,
                f"Surpassing Vanilla pp cap: {score.pp:.2f}",
            )
        elif score.mode == Mode.STD_RX and score.pp >= 1400:
            await app.usecases.user.restrict(
                user,
                f"Surpassing Relax pp cap: {score.pp:.2f}",
            )

    scores_collection = app.state.services.database.scores

    if score.status == ScoreStatus.BEST:
        await scores_collection.update_many(
            {
                "status": 2,
                "map_md5": beatmap.md5,
                "user_id": user.id,
                "mode": score.mode.value,
            },
            {"$set": {"status": 1}},
        )

    score.id = await scores_collection.count_documents({}) + 1
    await scores_collection.insert_one(score.dict())

    if score.passed:
        replay_data = await replay_file.read()

        if len(replay_data) < 24 and not user.privileges & Privileges.RESTRICTED:
            log.warning(f"{user} submitted a score without a replay")
            await app.usecases.user.restrict(user, "Submitted score without a replay")
        else:
            replay_file = REPLAYS_PATH / f"{score.id}.osr"
            replay_file.write_bytes(replay_data)

    old_stats = await app.usecases.stats.fetch(
        user.id,
        user.geolocation.country.acronym,
        score.mode,
    )
    stats = copy.copy(old_stats)

    stats.playcount += 1
    stats.total_score += score.score
    stats.total_hits += score.n300 + score.n100 + score.n50 + score.nmiss

    additive = score.score
    if score.old_best and score.status == ScoreStatus.BEST:
        additive -= score.old_best.score

    if score.passed and beatmap.status >= RankedStatus.RANKED:
        if beatmap.status == RankedStatus.RANKED:
            stats.ranked_score += additive

        if score.status == ScoreStatus.BEST and score.pp > 0.0:
            await app.usecases.stats.recalc(stats, score.mode, user.id)

        if score.max_combo > stats.max_combo:
            stats.max_combo = score.max_combo

    if score.passed and old_stats.pp != stats.pp:
        await app.usecases.stats.update_rank(
            stats,
            score.mode,
            user.id,
            user.geolocation.country.acronym,
        )

    await app.usecases.stats.save(stats, score.mode, user.id)
    await app.usecases.stats.refresh_stats(score.mode, user.id)

    if not user.privileges & Privileges.RESTRICTED:
        beatmap.plays += 1
        if score.passed:
            beatmap.passes += 1

        maps_collection = app.state.services.database.maps
        await maps_collection.update_one(
            {"md5": beatmap.md5},
            {"$set": {"plays": beatmap.plays, "passes": beatmap.passes}},
        )

    if score.status == ScoreStatus.BEST:
        leaderboard.add_score(score)
        score.rank = leaderboard.find_score_rank(score.id)

        if (
            beatmap.has_leaderboard
            and score.rank == 1
            and not user.privileges & Privileges.RESTRICTED
        ):
            announce_message = (
                f"{user.embed} has achieved #1 on {beatmap.embed} "
                f"with {score.mods!r} ({score.mode!r} | {score.pp:.2f}pp)"
            )

            await app.state.services.redis.publish(
                "send-public-message",
                orjson.dumps(
                    {
                        "channel": "#announcements",
                        "message": announce_message,
                    },
                ),
            )

    if not score.passed:
        return b"error: no"

    if beatmap.gives_pp and not user.privileges & Privileges.RESTRICTED:
        achievements_str = ""  # TODO: achievements

    if score.old_best:
        beatmap_ranking_chart = (
            chart_entry("rank", score.old_best.rank, score.rank),
            chart_entry("rankedScore", score.old_best.score, score.score),
            chart_entry("totalScore", score.old_best.score, score.score),
            chart_entry("maxCombo", score.old_best.max_combo, score.max_combo),
            chart_entry("accuracy", round(score.old_best.acc, 2), round(score.acc, 2)),
            chart_entry("pp", round(score.old_best.pp, 2), round(score.pp, 2)),
        )
    else:
        beatmap_ranking_chart = (
            chart_entry("rank", None, score.rank),
            chart_entry("rankedScore", None, score.score),
            chart_entry("totalScore", None, score.score),
            chart_entry("maxCombo", None, score.max_combo),
            chart_entry("accuracy", None, round(score.acc, 2)),
            chart_entry("pp", None, round(score.pp, 2)),
        )

    overall_ranking_chart = (
        chart_entry("rank", old_stats.global_rank, stats.global_rank),
        chart_entry("rankedScore", old_stats.ranked_score, stats.ranked_score),
        chart_entry("totalScore", old_stats.total_score, stats.total_score),
        chart_entry("maxCombo", old_stats.max_combo, stats.max_combo),
        chart_entry("accuracy", round(old_stats.accuracy, 2), round(stats.accuracy, 2)),
        chart_entry("pp", old_stats.pp, stats.pp),
    )

    submission_charts = [
        # beatmap info chart
        f"beatmapId:{beatmap.id}",
        f"beatmapSetId:{beatmap.set_id}",
        f"beatmapPlaycount:{beatmap.plays}",
        f"beatmapPasscount:{beatmap.passes}",
        f"approvedDate:{beatmap.last_update.isoformat()}",
        "\n",
        "chartId:beatmap",
        f"chartUrl:{beatmap.set_url}",
        "chartName:Beatmap Ranking",
        *beatmap_ranking_chart,
        f"onlineScoreId:{score.id}",
        "\n",
        "chartId:overall",
        f"chartUrl:https://{app.config.SERVER_DOMAIN}/u/{user.id}",
        "chartName:Overall Ranking",
        *overall_ranking_chart,
        f"achievements-new:{achievements_str}",
    ]

    end = time.perf_counter_ns()
    formatted_time = log.format_time(end - start)
    log.info(
        f"{user} submitted a {score.pp:.2f}pp {score.mode!r} score on {beatmap.full_name} in {formatted_time}",
    )

    return "|".join(submission_charts).encode()
