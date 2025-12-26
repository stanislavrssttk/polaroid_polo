import threading
from typing import Optional

import numpy as np
import soundfile as sf
import sounddevice as sd

from core.filters import peaking_eq_coeffs, BiquadState


class AudioEngine:
    def __init__(self):
        self.is_playing = False
        self.is_ab_original = False  # False = EQ, True = оригинал

        self._orig: Optional[np.ndarray] = None
        self._samplerate: int = 44100

        self._thread: Optional[threading.Thread] = None
        self._stop_flag = False

        self._volume = 1.0  # 0.0–1.0

        self._eq_coeffs = None
        self._eq_state: Optional[BiquadState] = None

    def set_volume(self, volume: float):
        volume = max(0.0, min(1.0, float(volume)))
        self._volume = volume

    def load_file(self, path: str):
        data, sr = sf.read(path, always_2d=True, dtype="float32")
        self._samplerate = int(sr)
        self._orig = data

        # сброс EQ состояния при загрузке нового файла
        self._eq_coeffs = None
        self._eq_state = None

    def set_peaking_eq(self, freq_hz: float, q: float, gain_db: float):
        if self._orig is None:
            return

        self._eq_coeffs = peaking_eq_coeffs(self._samplerate, freq_hz, q, gain_db)
        channels = int(self._orig.shape[1])
        self._eq_state = BiquadState(channels)

    def play(self):
        if self._orig is None:
            return
        if self.is_playing:
            return

        self._stop_flag = False
        self.is_playing = True

        self._thread = threading.Thread(target=self._play_loop, daemon=True)
        self._thread.start()

    def stop(self):
        if not self.is_playing:
            return

        self._stop_flag = True
        try:
            sd.stop()
        except Exception:
            pass

        self.is_playing = False

    def toggle_play(self):
        if self.is_playing:
            self.stop()
        else:
            self.play()

    def toggle_ab(self):
        self.is_ab_original = not self.is_ab_original

        # чтобы при переключении A/B не было “хвоста” состояния фильтра
        if not self.is_ab_original and self._orig is not None and self._eq_coeffs is not None:
            self._eq_state = BiquadState(int(self._orig.shape[1]))

    def _play_loop(self):
        if self._orig is None:
            self.is_playing = False
            return

        frames, channels = self._orig.shape
        block_size = 1024

        try:
            with sd.OutputStream(
                samplerate=self._samplerate,
                channels=channels,
                dtype="float32",
            ) as stream:
                idx = 0
                while not self._stop_flag:
                    if idx >= frames:
                        idx = 0

                    end = min(idx + block_size, frames)
                    chunk = self._orig[idx:end]
                    idx = end

                    # применяем EQ только в режиме B (EQ)
                    if (not self.is_ab_original) and (self._eq_coeffs is not None) and (self._eq_state is not None):
                        chunk = self._eq_state.process_block(chunk, self._eq_coeffs)

                    stream.write(chunk * self._volume)
        except Exception:
            pass

        self.is_playing = False
