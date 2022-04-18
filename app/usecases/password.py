from __future__ import annotations

import asyncio

import bcrypt


async def hash_password(plain_password: bytes) -> bool:
    loop = asyncio.get_running_loop()
    result = await loop.run_in_executor(
        None,
        bcrypt.hashpw,
        plain_password,
        bcrypt.gensalt(),
    )

    return result
