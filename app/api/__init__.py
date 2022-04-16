from __future__ import annotations

from fastapi import APIRouter

from app.api import leaderboards

router = APIRouter()
router.add_api_route("/web/osu-osz2-getscores.php", leaderboards.get_leaderboard)
