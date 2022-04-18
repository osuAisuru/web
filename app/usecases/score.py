from __future__ import annotations

import app.state
from app.constants.mode import Mode
from app.constants.privileges import Privileges
from app.objects.score import Score
from app.objects.score import ScoreStatus


async def calculate_rank(score: Score) -> int:
    if score.mode > Mode.MANIA:
        args = {"pp": {"$gt": score.pp}}
    else:
        args = {"score": {"$gt": score.score}}

    scores_collection = app.state.services.database.scores
    better_scores = scores_collection.find(
        {"map_md5": score.map_md5, "mode": score.mode, "status": 2} | args,
    )

    user_collection = app.state.services.database.users
    users = {
        user["id"]: user["privileges"]
        async for user in user_collection.find(
            {"id": {"$in": [score["user_id"] async for score in better_scores]}},
        )
    }

    better_score_count = len(
        score
        async for score in better_scores
        if Privileges(users[score["user_id"]]) & Privileges.DISALLOWED == 0
    )

    return better_score_count + 1


def calculate_accuracy(score: Score) -> float:
    vanilla_mode = score.mode.as_vn

    n300 = score.n300
    n100 = score.n100
    n50 = score.n50

    ngeki = score.ngeki
    nkatu = score.nkatu

    nmiss = score.nmiss

    if vanilla_mode == 0:  # osu!
        total = n300 + n100 + n50 + nmiss

        if total == 0:
            return 0.0

        return (
            100.0 * ((n300 * 300.0) + (n100 * 100.0) + (n50 * 50.0)) / (total * 300.0)
        )

    elif vanilla_mode == 1:  # osu!taiko
        total = n300 + n100 + nmiss

        if total == 0:
            return 0.0

        return 100.0 * ((n100 * 0.5) + n300) / total

    elif vanilla_mode == 2:  # osu!catch
        total = n300 + n100 + n50 + nkatu + nmiss

        if total == 0:
            return 0.0

        return 100.0 * (n300 + n100 + n50) / total

    elif vanilla_mode == 3:  # osu!mania
        total = n300 + n100 + n50 + ngeki + nkatu + nmiss

        if total == 0:
            return 0.0

        return (
            100.0
            * (
                (n50 * 50.0)
                + (n100 * 100.0)
                + (nkatu * 200.0)
                + ((n300 + ngeki) * 300.0)
            )
            / (total * 300.0)
        )


def calculate_status(score: Score) -> None:
    if score.old_best:
        if score.pp > score.old_best.pp:
            score.status = ScoreStatus.BEST
            score.old_best.status = ScoreStatus.SUBMITTED
        else:
            score.status = ScoreStatus.SUBMITTED
    else:
        score.status = ScoreStatus.BEST


async def increment_replay_views(score_id: int) -> None:
    scores_collection = app.state.services.database.scores
    await scores_collection.update_one({"id": score_id}, {"$inc": {"replay_views": 1}})
