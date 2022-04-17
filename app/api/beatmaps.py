from __future__ import annotations

from fastapi import Depends
from fastapi import Query
from pydantic import BaseModel

import app.state
import log
from app.constants.mode import Mode
from app.objects.user import User
from app.utils import authenticate_user


def bancho_to_osu_api_status(bancho_status: int) -> int:
    return {
        0: 0,
        2: 1,
        3: 2,
        4: 3,
        5: 4,
    }[bancho_status]


class OsuBeatmapRequestForm(BaseModel):
    Filenames: list[str]
    Ids: list[int]


async def get_beatmap_info(
    form_data: OsuBeatmapRequestForm,
    user: User = Depends(authenticate_user(Query, "u", "h")),
):
    map_count = len(form_data.Filenames) + len(form_data.Ids)
    log.info(f"{user} requested {map_count} maps")

    ret = []

    for idx, map_filename in enumerate(form_data.Filenames):
        maps_collection = app.state.services.database.maps
        document = await maps_collection.find_one({"filename": map_filename})
        if not document:
            continue

        document["status"] = bancho_to_osu_api_status(document["status"])

        grades = ["N", "N", "N", "N"]

        using_relax = user.status.mode.as_vn() != user.status.mode.value

        if using_relax:
            modes = [Mode.STD_RX, Mode.TAIKO_RX, Mode.CATCH_RX]
        else:
            modes = [Mode.STD, Mode.TAIKO, Mode.CATCH, Mode.MANIA]

        scores_collection = app.state.services.database.scores
        scores = scores_collection.find(
            {
                "user_id": user.id,
                "map_md5": document["md5"],
                "mode": {"$in": [mode.value for mode in modes]},
                "status": 2,
            },
        )

        async for score in scores:
            grade_idx = modes.index(Mode(score["mode"]))
            grades[grade_idx] = score["grade"]

        formatted_document = {
            "idx": idx,
            "id": document["id"],
            "set_id": document["set_id"],
            "md5": document["md5"],
            "status": document["status"],
            "grades": "|".join(grades),
        }

        ret.append(
            "{idx}|{id}|{set_id}|{md5}|{status}|{grades}".format(**formatted_document),
        )

    return "\n".join(ret).encode()
