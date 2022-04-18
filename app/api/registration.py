from __future__ import annotations

import hashlib
import re
import time
from collections import defaultdict
from typing import Mapping

from fastapi import Form
from fastapi import Header
from fastapi import Request
from fastapi import Response
from fastapi import status
from fastapi.responses import ORJSONResponse

import app.config
import app.state
import app.usecases
import log
from app.constants.mode import Mode
from app.constants.privileges import Privileges

USERNAME = re.compile(r"^[\w \[\]-]{2,15}$")
EMAIL = re.compile(r"^[^@\s]{1,200}@[^@\s\.]{1,30}(?:\.[^@\.\s]{2,24})+$")


async def user_registration(
    request: Request,
    username: str = Form(..., alias="user[username]"),
    email: str = Form(..., alias="user[user_email]"),
    pw_plaintext: str = Form(..., alias="user[password]"),
    check: int = Form(...),
):
    if not app.config.INGAME_REGISTRATION:
        return

    safe_name = username.lower().replace(" ", "_")

    if not all((username, email, pw_plaintext)):
        return Response(
            content=b"Missing required params.",
            status_code=status.HTTP_400_BAD_REQUEST,
        )

    errors: Mapping[str, list[str]] = defaultdict(list)
    users_collection = app.state.services.database.users

    if not USERNAME.match(username):
        errors["username"].append("Must be 2-15 characters in length.")
    else:
        if await users_collection.find_one({"safe_name": safe_name}):
            errors["username"].append("Username already taken by another user.")

    if not EMAIL.match(email):
        errors["user_email"].append("Email already taken by another user.")
    else:
        if await users_collection.find_one({"email": email}):
            errors["user_email"].append("Email already taken by another user.")

    if not 8 <= len(pw_plaintext) <= 32:
        errors["password"].append("Must be 8-32 characters in length.")

    if errors:
        errors = {k: ["\n".join(v)] for k, v in errors.items()}

        return ORJSONResponse(
            content={"form_error": {"user": errors}},
            status_code=status.HTTP_400_BAD_REQUEST,
        )

    if check == 0:
        password_md5 = hashlib.md5(pw_plaintext.encode()).hexdigest().encode()
        hashed_password = await app.usecases.password.hash_password(password_md5)

        geolocation = app.usecases.geolocation.from_ip(request.headers)

        users = [user["id"] async for user in users_collection.find({})]
        user_id = len([user for user in users if user != 1]) + 1

        # math fuckery to deal with the ID 2 skip
        if user_id == 2:
            user_id = 3
        else:
            user_id = user_id + 2

        await users_collection.insert_one(
            {
                "id": user_id,
                "name": username,
                "safe_name": safe_name,
                "password_bcrypt": hashed_password,
                "register_time": int(time.time()),
                "latest_activity": int(time.time()),
                "email": email,
                "privileges": Privileges.NORMAL,
                "silence_end": 0,
                "friends": [],
                "country": geolocation.country.acronym,
                "blocked": [],
            },
        )

        stats_collection = app.state.services.database.ustats
        await stats_collection.insert_many(
            [
                {
                    "user_id": user_id,
                    "total_score": 0,
                    "ranked_score": 0,
                    "accuracy": 0,
                    "pp": 0,
                    "max_combo": 0,
                    "total_hits": 0,
                    "playcount": 0,
                    "playtime": 0,
                    "mode": mode.value,
                }
                for mode in Mode
            ],
        )

        log.info(f"<{username} ({user_id})> has registered!")

    return b"ok"
