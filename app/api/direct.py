from __future__ import annotations

from typing import Any
from typing import Optional
from urllib.parse import unquote_plus

from aiohttp import ClientSession
from fastapi import Depends
from fastapi import Query
from fastapi import status
from fastapi.responses import RedirectResponse

import app.config
import app.usecases
from app.objects.beatmap import RankedStatus
from app.objects.user import User
from app.utils import authenticate_user

DIRECT_SET_INFO_FMTSTR = (
    "{SetID}.osz|{Artist}|{Title}|{Creator}|"
    "{RankedStatus}|10.0|{LastUpdate}|{SetID}|"
    "0|{HasVideo}|0|0|0|{diffs}"
)

DIRECT_MAP_INFO_FMTSTR = (
    "[{DifficultyRating:.2f}⭐] {DiffName} "
    "{{cs: {CS} / od: {OD} / ar: {AR} / hp: {HP}}}@{Mode}"
)


async def osu_direct(
    user: User = Depends(authenticate_user(Query, "u", "h")),
    ranked_status: int = Query(..., alias="r", ge=0, le=8),
    query: str = Query(..., alias="q"),
    mode: int = Query(..., alias="m", ge=-1, le=3),
    page_num: int = Query(..., alias="p"),
):
    search_url = f"{app.config.MIRROR_URL}/api/search"

    params: dict[str, Any] = {"amount": 100, "offset": page_num * 100}

    if unquote_plus(query) not in ("Newest", "Top Rated", "Most Played"):
        params["query"] = query

    if mode != -1:
        params["mode"] = mode

    if ranked_status != 4:
        params["status"] = RankedStatus.from_direct(ranked_status).osu_api

    if False:  # TODO: workout why their response isn't liked by osu!
        if "catboy.best" in search_url:
            params["raw"] = "1"  # mino cana format to direct for us

        if "raw" in params:
            param_str = "&".join(f"{k}={v}" for k, v in params.items())
            url = f"{search_url}?{param_str}"

            return RedirectResponse(
                url=url,
                status_code=status.HTTP_301_MOVED_PERMANENTLY,
            )

    async with ClientSession() as session:
        async with session.get(search_url, params=params) as response:
            if response.status != status.HTTP_200_OK:
                return b"-1\nFailed to retrieve data from the beatmap mirror."

            result = await response.json()

    result_len = len(result)
    ret = [f"{'101' if result_len == 100 else result_len}"]

    for bmap in result:
        if not bmap["ChildrenBeatmaps"]:
            continue

        bmap["HasVideo"] = "0"  # XX: does mino support this?

        diff_sorted_maps = sorted(
            bmap["ChildrenBeatmaps"],
            key=lambda x: x["DifficultyRating"],
        )

        diffs_str = ",".join(
            DIRECT_MAP_INFO_FMTSTR.format(**bm) for bm in diff_sorted_maps
        )
        ret.append(DIRECT_SET_INFO_FMTSTR.format(**bmap, diffs=diffs_str))

    return "\n".join(ret).encode()


async def beatmap_card(
    user: User = Depends(authenticate_user(Query, "u", "h")),
    map_set_id: Optional[int] = Query(None, alias="s"),
    map_id: Optional[int] = Query(None, alias="b"),
):
    if map_set_id is not None:
        func, arg = (app.usecases.beatmap.fetch_by_set_id, map_set_id)
    elif map_id is not None:
        func, arg = (app.usecases.beatmap.fetch_by_id, map_id)
    else:
        return

    beatmap = await func(arg)
    if not beatmap:
        return

    return (
        "{set_id}.osz|{artist}|{title}|{creator}|"
        "{status}|10.0|{last_update}|{set_id}|"
        "0|0|0|0|0".format(**beatmap.dict())
    ).encode()
