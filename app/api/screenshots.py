from __future__ import annotations

import secrets
from pathlib import Path
from typing import Literal

from fastapi import Depends
from fastapi import File
from fastapi import Form
from fastapi import Path as URLPath
from fastapi import Response
from fastapi import status
from fastapi import UploadFile
from fastapi.responses import FileResponse

import app.utils
import log
from app.objects.user import User
from app.utils import authenticate_user

DATA_PATH = Path.cwd() / "data"
SCREENSHOTS_PATH = DATA_PATH / "screenshots"

for path in (DATA_PATH, SCREENSHOTS_PATH):
    if not path.exists():
        path.mkdir(parents=True)


async def upload_screenshot(
    user: User = Depends(authenticate_user(Form, "u", "p")),
    endpoint_version: int = Form(..., alias="v"),
    screenshot_file: UploadFile = File(..., alias="ss"),
):
    if endpoint_version != 1:
        return Response(
            content=b"error: no",
            status_code=status.HTTP_400_BAD_REQUEST,
        )

    screenshot_bytes = await screenshot_file.read()
    if len(screenshot_bytes) > (4 * 1024 * 1024):
        return Response(
            content=b"Screenshot too large",
            status_code=status.HTTP_400_BAD_REQUEST,
        )

    if app.utils.has_jpeg_headers_and_trailers(screenshot_bytes):
        extension = "jpeg"
    elif app.utils.has_png_headers_and_trailers(screenshot_bytes):
        extension = "png"
    else:
        return Response(
            content=b"Invalid file type",
            status_code=status.HTTP_400_BAD_REQUEST,
        )

    while True:
        filename = f"{secrets.token_urlsafe(6)}.{extension}"
        ss_file = SCREENSHOTS_PATH / filename
        if not ss_file.exists():
            break

    ss_file.write_bytes(screenshot_bytes)
    log.info(f"{user} uploaded screenshot {filename}")
    return Response(filename.encode())


async def view_screenshot(
    screenshot_id: str = URLPath(..., regex=r"[a-zA-Z0-9-_]{8}"),
    extension: Literal["jpg", "jpeg", "png"] = URLPath(...),
):
    ss_file = SCREENSHOTS_PATH / f"{screenshot_id}.{extension}"

    if not ss_file.exists():
        return Response(
            content=b"Screenshot not found",
            status_code=status.HTTP_404_NOT_FOUND,
        )

    return FileResponse(
        path=ss_file,
        media_type=app.utils.get_media_type(extension),
    )
