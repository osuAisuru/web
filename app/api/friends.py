from __future__ import annotations

from fastapi import Depends
from fastapi import Query

from app.objects.user import User
from app.utils import authenticate_user


async def get_friends(user: User = Depends(authenticate_user(Query, "u", "p"))):
    return "\n".join(map(str, user.friends)).encode()
