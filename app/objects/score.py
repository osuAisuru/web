from __future__ import annotations

import functools
from dataclasses import dataclass
from datetime import datetime
from enum import IntEnum
from typing import Any
from typing import Optional

from app.constants.flags import ClientFlags
from app.constants.mode import Mode
from app.constants.mods import Mods
from app.constants.privileges import Privileges
from app.objects.user import User


class Grade(IntEnum):
    N = 0
    F = 1
    D = 2
    C = 3
    B = 4
    A = 5
    S = 6  # S
    SH = 7  # HD S
    X = 8  # SS
    XH = 9  # HD SS

    @classmethod
    @functools.cache
    def from_str(cls, s: str) -> Grade:
        return {
            "xh": Grade.XH,
            "x": Grade.X,
            "sh": Grade.SH,
            "s": Grade.S,
            "a": Grade.A,
            "b": Grade.B,
            "c": Grade.C,
            "d": Grade.D,
            "f": Grade.F,
            "n": Grade.N,
        }[s.lower()]


class ScoreStatus(IntEnum):
    NOT_SUBMITTED = 0
    SUBMITTED = 1
    BEST = 2


@dataclass
class Score:
    id: int
    map_md5: str

    # TODO: don't fucking store these here???
    user_id: int
    username: str
    user_priv: Privileges
    user_country: str

    mode: Mode
    mods: Mods

    pp: float
    sr: float
    score: int
    max_combo: int
    acc: float

    n300: int
    n100: int
    n50: int
    nmiss: int
    ngeki: int
    nkatu: int

    grade: Grade

    passed: bool
    perfect: bool
    status: ScoreStatus

    time: datetime
    time_elapsed: int

    client_flags: ClientFlags
    client_checksum: str

    replay_views: int

    rank: int = 0
    old_best: Optional[Score] = None

    def osu_string(self, username: str, rank: int) -> str:
        if self.mode > Mode.MANIA:
            score = int(self.pp)
        else:
            score = self.score

        timestamp = int(self.time.timestamp())

        return (
            f"{self.id}|{username}|{score}|{self.max_combo}|{self.n50}|{self.n100}|{self.n300}|{self.nmiss}|"
            f"{self.nkatu}|{self.ngeki}|{self.perfect}|{int(self.mods)}|{self.user_id}|{rank}|{timestamp}|"
            "1"  # has replay
        )

    def dict(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "map_md5": self.map_md5,
            "user_id": self.user_id,
            "mode": self.mode.value,
            "mods": self.mods.value,
            "pp": self.pp,
            "score": self.score,
            "max_combo": self.max_combo,
            "acc": self.acc,
            "n300": self.n300,
            "n100": self.n100,
            "n50": self.n50,
            "nmiss": self.nmiss,
            "ngeki": self.ngeki,
            "nkatu": self.nkatu,
            "grade": self.grade.value,
            "passed": self.passed,
            "perfect": self.perfect,
            "status": self.status.value,
            "time": self.time.isoformat(),
            "time_elapsed": self.time_elapsed,
            "client_flags": self.client_flags.value,
            "client_checksum": self.client_checksum,
            "replay_views": self.replay_views,
        }

    @classmethod
    async def from_row(cls, row: dict[str, Any]):
        score = Score(
            id=row["score"],
            map_md5=row["map_md5"],
            user_id=row["user_id"],
            username=row["username"],
            user_priv=Privileges(row["user_priv"]),
            user_country=row["user_country"],
            mode=Mode(row["mode"]),
            mods=Mods(row["mods"]),
            pp=row["pp"],
            sr=0.0,  # TODO
            score=row["score"],
            max_combo=row["max_combo"],
            acc=row["acc"],
            n300=row["n300"],
            n100=row["n100"],
            n50=row["n50"],
            nmiss=row["nmiss"],
            ngeki=row["ngeki"],
            nkatu=row["nkatu"],
            grade=Grade(row["grade"]),
            passed=row["passed"],
            perfect=row["perfect"],
            status=ScoreStatus(row["status"]),
            time=datetime.fromisoformat(row["time"]),
            time_elapsed=row["time_elapsed"],
            client_flags=ClientFlags(row["client_flags"]),
            client_checksum=row["client_checksum"],
            replay_views=row["replay_views"],
        )

        return score

    @classmethod
    def from_submission(cls, data: list[str], map_md5: str, user: User) -> Score:
        return Score(
            id=0,  # set later
            map_md5=map_md5,
            user_id=user.id,
            username=user.name,
            user_priv=user.privileges,
            user_country=user.geolocation.country.acronym,
            mode=Mode.from_lb(int(data[13]), int(data[11])),
            mods=Mods(int(data[11])),
            pp=0.0,  # set later
            sr=0.0,  # set later
            score=int(data[7]),
            max_combo=int(data[8]),
            acc=0.0,  # set later
            n300=int(data[1]),
            n100=int(data[2]),
            n50=int(data[3]),
            nmiss=int(data[6]),
            ngeki=int(data[4]),
            nkatu=int(data[5]),
            grade=Grade.from_str(data[10]),
            passed=data[12] == "True",
            perfect=data[9] == "True",
            status=ScoreStatus.NOT_SUBMITTED,  # set later
            time=datetime.now(),
            time_elapsed=0,  # set later
            client_flags=ClientFlags(data[15].count(" ") & ~4),
            client_checksum=data[0],
            replay_views=0,  # new score so its gonna be 0
        )
