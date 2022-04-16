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
from app.constants.status import Status
from app.objects.user import User


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
        async with ClientSession(connector=TCPConnector(verify_ssl=False)) as session:
            async with session.get(
                f"https://cho_api.{app.config.SERVER_DOMAIN}/user-auth",
                params={
                    "name": name,
                    "password": password_md5,
                    "key": app.config.API_SECRET,
                },
            ) as resp:
                if not resp:
                    raise HTTPException(
                        status_code=status.HTTP_401_UNAUTHORIZED,
                        detail=error_text,
                    )

                json = await resp.json()
                if json["status"] != "ok":
                    raise HTTPException(
                        status_code=status.HTTP_401_UNAUTHORIZED,
                        detail=error_text,
                    )

                json["user"]["status"] = Status.from_dict(json["user"]["status"])
                return User(**json["user"])

    return wrapper
