from __future__ import annotations

from typing import Awaitable
from typing import Callable


PubsubHandler = Callable[[str], Awaitable[None]]
