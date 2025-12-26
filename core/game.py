import random
from dataclasses import dataclass

from core.scoring import Scoring, cents_error


@dataclass
class GameRoundResult:
    true_freq: float
    guessed_freq: float
    err_cents: float
    err_hz: float

    true_gain_db: float
    guessed_gain_db: float
    err_gain_db: float

    gained: int
    total_score: int
    combo: int
    multiplier: float


class Game:
    def __init__(self, freq_min: float = 200.0, freq_max: float = 8000.0):
        self.freq_min = freq_min
        self.freq_max = freq_max

        self.scoring = Scoring()
        self.current_freq: float | None = None
        self.current_gain_db: float | None = None

    def new_round(self, gain_min_db: float = -15.0, gain_max_db: float = 15.0) -> tuple[float, float]:
        self.current_freq = self._random_freq()
        self.current_gain_db = random.choice([gain_min_db, gain_max_db])
        return self.current_freq, self.current_gain_db

    def _random_freq(self) -> float:
        f1, f2 = self.freq_min, self.freq_max
        r = random.random()
        return f1 * (f2 / f1) ** r

    def submit_answer(self, guessed_freq: float, guessed_gain_db: float) -> GameRoundResult | None:
        if self.current_freq is None or self.current_gain_db is None:
            return None

        true_f = self.current_freq
        true_g = self.current_gain_db

        err_c = cents_error(true_f, guessed_freq)
        err_hz = guessed_freq - true_f

        err_g = guessed_gain_db - true_g

        score_info = self.scoring.register_result(err_cents=err_c, err_gain_db=err_g)

        return GameRoundResult(
            true_freq=true_f,
            guessed_freq=guessed_freq,
            err_cents=err_c,
            err_hz=err_hz,
            true_gain_db=true_g,
            guessed_gain_db=guessed_gain_db,
            err_gain_db=err_g,
            gained=score_info["gained"],
            total_score=score_info["score"],
            combo=score_info["combo"],
            multiplier=score_info["multiplier"],
        )

    def reset(self):
        self.scoring.reset()
        self.current_freq = None
        self.current_gain_db = None
