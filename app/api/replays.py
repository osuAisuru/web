from __future__ import annotations

from pathlib import Path

from fastapi import Depends
from fastapi import Query
from fastapi.responses import FileResponse

import app.usecases
from app.objects.user import User
from app.utils import authenticate_user

DATA_PATH = Path.cwd() / "data"
REPLAYS_PATH = DATA_PATH / "replays"


async def get_replay(
    user: User = Depends(authenticate_user(Query, "u", "h")),
    mode: int = Query(..., alias="m", ge=0, le=3),
    score_id: int = Query(..., alias="c", min=0, max=9_223_372_036_854_775_807),
):
    replay_file = REPLAYS_PATH / f"{score_id}.osr"
    if not replay_file.exists():
        return

    await app.usecases.score.increment_replay_views(score_id)
    return FileResponse(replay_file)
