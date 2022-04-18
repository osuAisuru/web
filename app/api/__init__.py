from __future__ import annotations

from fastapi import APIRouter
from fastapi import Path
from fastapi import Request
from fastapi import Response
from fastapi import status
from fastapi.responses import RedirectResponse

from . import beatmaps
from . import comments
from . import direct
from . import favourites
from . import friends
from . import lastfm
from . import leaderboards
from . import ratings
from . import redis
from . import registration
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
router.add_api_route("/web/osu-addfavourite.php", favourites.add_favourite)

router.add_api_route("/web/lastfm.php", lastfm.last_fm)

router.add_api_route("/web/osu-search.php", direct.osu_direct)
router.add_api_route("/web/osu-search-set.php", direct.beatmap_card)
router.add_api_route("/d/{set_id}", direct.download_map)

router.add_api_route("/web/osu-getreplay.php", replays.get_replay)

router.add_api_route("/web/osu-rate.php", ratings.osu_rate)

router.add_api_route(
    "/web/osu-comment.php",
    comments.osu_comment,
    methods=["POST"],
)

router.add_api_route(
    "/users",
    registration.user_registration,
    methods=["POST"],
)

# TODO: maybe add mark as read and seasonals

""" hidden endpoints which are static/redirects """


@router.get("/web/bancho-connect.php")
async def bancho_connect():
    return b""


@router.get("/p/doyoureallywanttoaskpeppy")
async def peppy():
    return b"This is a peppy skill issue, please ignore."


async def osu_redirect(request: Request, _: int = Path(...)):
    return RedirectResponse(
        url=f"https://osu.ppy.sh{request['path']}",
        status_code=status.HTTP_301_MOVED_PERMANENTLY,
    )


for pattern in (
    "/beatmapsets/{_}",
    "/beatmaps/{_}",
    "/community/forums/topics/{_}",
    "/web/maps/{_}",
):
    router.get(pattern)(osu_redirect)


@router.post("/difficulty-rating")
async def difficulty_rating(request: Request):
    return RedirectResponse(
        url=f"https://osu.ppy.sh{request['path']}",
        status_code=status.HTTP_307_TEMPORARY_REDIRECT,
    )
