from __future__ import annotations

from fastapi import APIRouter
from fastapi import Response

from . import friends
from . import leaderboards
from . import redis
from . import score_submission
from . import screenshot

router = APIRouter(default_response_class=Response)
router.add_api_route("/web/osu-osz2-getscores.php", leaderboards.get_leaderboard)
router.add_api_route(
    "/web/osu-submit-modular-selector.php",
    score_submission.submit_score,
    methods=["POST"],
)
router.add_api_route(
    "/web/osu-screenshot.php",
    screenshot.upload_screenshot,
    methods=["POST"],
)
router.add_api_route("/web/osu-getfriends.php", friends.get_friends)
