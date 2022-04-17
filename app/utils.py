from __future__ import annotations

from functools import cache
from typing import Any
from typing import Awaitable
from typing import Callable
from typing import Optional

from aiohttp import ClientSession
from aiohttp import TCPConnector
from fastapi import HTTPException
from fastapi import status

import app.config
from app.constants.privileges import Privileges
from app.constants.status import Status
from app.objects.geolocation import Geolocation
from app.objects.user import User


async def get_user(name: str, password_md5: str) -> Optional[User]:
    async with ClientSession(connector=TCPConnector(verify_ssl=False)) as session:
        async with session.get(
            f"http://127.0.0.1:9823/user-auth",
            headers={"Host": f"cho_api.{app.config.SERVER_DOMAIN}"},
            params={
                "name": name,
                "password": password_md5,
                "key": str(app.config.API_SECRET),
            },
        ) as resp:
            if not resp:
                return None

            json = await resp.json()
            if json["status"] != "ok":
                return None

            json["user"]["status"] = Status.from_dict(json["user"]["status"])
            json["user"]["privileges"] = Privileges(json["user"]["privileges"])
            json["user"]["geolocation"] = Geolocation.from_dict(
                json["user"]["geolocation"],
            )
            return User(**json["user"])


@cache
def authenticate_user(
    param_function: Callable[..., Any],
    name_arg: str = "u",
    password_arg: str = "p",
    error_text: Optional[Any] = None,
) -> Callable[[str, str], Awaitable[User]]:
    async def wrapper(
        name: str = param_function(..., alias=name_arg),
        password_md5: str = param_function(..., alias=password_arg),
    ):
        if not (user := await get_user(name, password_md5)):
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail=error_text,
            )

        return user

    return wrapper


def get_media_type(extension: str) -> Optional[str]:
    if extension in ("jpg", "jpeg"):
        return "image/jpeg"
    elif extension == "png":
        return "image/png"


def has_jpeg_headers_and_trailers(data_view: memoryview) -> bool:
    return data_view[:4] == b"\xff\xd8\xff\xe0" and data_view[6:11] == b"JFIF\x00"


def has_png_headers_and_trailers(data_view: memoryview) -> bool:
    return (
        data_view[:8] == b"\x89PNG\r\n\x1a\n"
        and data_view[-8] == b"\x49END\xae\x42\x60\x82"
    )
