from math import log2


class Scoring:
    def __init__(self):
        self.score = 0
        self.combo = 0
        self.multiplier = 1.0

    def reset(self):
        self.score = 0
        self.combo = 0
        self.multiplier = 1.0

    def _tier_freq(self, err_cents_abs: float) -> int:
        if err_cents_abs < 100:
            return 3
        if err_cents_abs < 300:
            return 2
        if err_cents_abs < 600:
            return 1
        return 0

    def _tier_gain(self, err_gain_abs: float) -> int:
        if err_gain_abs < 1.0:
            return 3
        if err_gain_abs < 3.0:
            return 2
        if err_gain_abs < 6.0:
            return 1
        return 0

    def register_result(self, err_cents: float, err_gain_db: float) -> dict:
        ec = abs(err_cents)
        eg = abs(err_gain_db)

        tier = min(self._tier_freq(ec), self._tier_gain(eg))

        if tier == 3:
            base = 90
            self.combo += 1
        elif tier == 2:
            base = 60
            self.combo += 1
        elif tier == 1:
            base = 30
            self.combo = max(0, self.combo - 1)
        else:
            base = 5
            self.combo = 0

        self.multiplier = 1.0 + self.combo * 0.1
        gained = int(base * self.multiplier)
        self.score += gained

        return {
            "gained": gained,
            "score": self.score,
            "combo": self.combo,
            "multiplier": self.multiplier,
        }


def cents_error(true_freq: float, guessed_freq: float) -> float:
    if true_freq <= 0 or guessed_freq <= 0:
        return 0.0
    return 1200.0 * log2(guessed_freq / true_freq)
