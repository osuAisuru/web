from __future__ import annotations

from pathlib import Path

from aisuru_pp_py import Calculator
from aisuru_pp_py import ScoreParams

from app.objects.score import Score


def calculate_score(score: Score, osu_file_path: Path) -> None:
    calculator = Calculator(str(osu_file_path))

    score_params = ScoreParams(
        mods=score.mods.value,
        acc=score.acc,
        nMisses=score.nmiss,
        combo=score.max_combo,
    )

    (result,) = calculator.calculate(score_params)

    score.pp = result.pp
    score.sr = result.stars
