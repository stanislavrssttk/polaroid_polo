from __future__ import annotations

from dataclasses import dataclass
from math import pi, sin, cos, sqrt
import numpy as np


@dataclass(frozen=True)
class BiquadCoeffs:
    b0: float
    b1: float
    b2: float
    a1: float
    a2: float


def peaking_eq_coeffs(fs: float, f0: float, q: float, gain_db: float) -> BiquadCoeffs:
    f0 = float(max(1.0, min(f0, fs * 0.499)))
    q = float(max(1e-4, q))
    gain_db = float(gain_db)

    a = 10.0 ** (gain_db / 40.0)
    w0 = 2.0 * pi * f0 / fs
    alpha = sin(w0) / (2.0 * q)

    b0 = 1.0 + alpha * a
    b1 = -2.0 * cos(w0)
    b2 = 1.0 - alpha * a

    a0 = 1.0 + alpha / a
    a1 = -2.0 * cos(w0)
    a2 = 1.0 - alpha / a

    b0 /= a0
    b1 /= a0
    b2 /= a0
    a1 /= a0
    a2 /= a0

    return BiquadCoeffs(b0=b0, b1=b1, b2=b2, a1=a1, a2=a2)


def apply_biquad(x: np.ndarray, c: BiquadCoeffs) -> np.ndarray:
    if x.ndim != 2:
        raise ValueError("x must be [frames, channels]")

    y = np.empty_like(x, dtype=np.float32)

    b0, b1, b2, a1, a2 = c.b0, c.b1, c.b2, c.a1, c.a2
    frames, ch = x.shape

    for k in range(ch):
        x1 = 0.0
        x2 = 0.0
        y1 = 0.0
        y2 = 0.0
        for n in range(frames):
            xn = float(x[n, k])
            yn = b0 * xn + b1 * x1 + b2 * x2 - a1 * y1 - a2 * y2
            y[n, k] = yn
            x2, x1 = x1, xn
            y2, y1 = y1, yn

    return y.astype(np.float32)

class BiquadState:
    def __init__(self, channels: int):
        self.x1 = [0.0] * channels
        self.x2 = [0.0] * channels
        self.y1 = [0.0] * channels
        self.y2 = [0.0] * channels

    def process_block(self, x, c):
        frames, ch = x.shape
        y = np.empty_like(x)

        for k in range(ch):
            x1, x2 = self.x1[k], self.x2[k]
            y1, y2 = self.y1[k], self.y2[k]

            for n in range(frames):
                xn = float(x[n, k])
                yn = (
                    c.b0 * xn +
                    c.b1 * x1 +
                    c.b2 * x2 -
                    c.a1 * y1 -
                    c.a2 * y2
                )
                y[n, k] = yn
                x2, x1 = x1, xn
                y2, y1 = y1, yn

            self.x1[k], self.x2[k] = x1, x2
            self.y1[k], self.y2[k] = y1, y2

        return y
