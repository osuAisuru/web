from __future__ import annotations

from fastapi import APIRouter
from fastapi import Response

from . import beatmaps
from . import direct
from . import favourites
from . import friends
from . import lastfm
from . import leaderboards
from . import ratings
from . import redis
from . import replays
from . import score_submission
from . import screenshots

router = APIRouter(default_response_class=Response)

router.add_api_route("/web/osu-osz2-getscores.php", leaderboards.get_leaderboard)
router.add_api_route(
    "/web/osu-submit-modular-selector.php",
    score_submission.submit_score,
    methods=["POST"],
)

router.add_api_route("/ss/{screenshot_id}.{extension}", screenshots.view_screenshot)
router.add_api_route(
    "/web/osu-screenshot.php",
    screenshots.upload_screenshot,
    methods=["POST"],
)

router.add_api_route("/web/osu-getfriends.php", friends.get_friends)

router.add_api_route(
    "/web/osu-getbeatmapinfo.php",
    beatmaps.get_beatmap_info,
    methods=["POST"],
)

router.add_api_route("/web/osu-getfavourites.php", favourites.get_favourites)
router.add_api_route(
    "/web/osu-addfavourite.php",
    favourites.add_favourite,
)

router.add_api_route("/web/lastfm.php", lastfm.last_fm)

router.add_api_route("/web/osu-search.php", direct.osu_direct)
router.add_api_route("/web/osu-search-set.php", direct.beatmap_card)
router.add_api_route("/d/{set_id}", direct.download_map)

router.add_api_route("/web/osu-getreplay.php", replays.get_replay)

router.add_api_route("/web/osu-rate.php", ratings.osu_rate)
