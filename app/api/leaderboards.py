from __future__ import annotations

from fastapi import Depends
from fastapi import Query

from app.constants.mode import Mode
from app.constants.mods import Mods
from app.objects.user import User
from app.utils import authenticate_user


async def get_leaderboard(
    user: User = Depends(authenticate_user(Query, "us", "ha")),
    requesting_from_editor_song_select: bool = Query(..., alias="s"),
    leaderboard_version: int = Query(..., alias="vv"),
    leaderboard_type: int = Query(..., alias="v", ge=0, le=4),
    map_md5: str = Query(..., alias="c", min_length=32, max_length=32),
    map_filename: str = Query(..., alias="f"),
    mode_arg: int = Query(..., alias="m", ge=0, le=3),
    map_set_id: int = Query(..., alias="i", ge=-1, le=2_147_483_647),
    mods_arg: int = Query(..., alias="mods", ge=0, le=2_147_483_647),
    map_package_hash: str = Query(..., alias="h"),
    aqn_files_found: bool = Query(..., alias="a"),
):
    mode = Mode.from_lb(mode_arg, mods_arg)
    mods = Mods(mods_arg)

    if mode != user.status.mode or mods != user.status.mods:
        user.status.mode = mode
        user.status.mods = mods

        await user.update_status()
