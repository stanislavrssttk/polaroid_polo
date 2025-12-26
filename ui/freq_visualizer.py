from math import log10

from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QPainter, QColor, QPen
from PySide6.QtWidgets import QWidget


class FreqVisualizer(QWidget):
    frequencyHovered = Signal(float, float)   # freq_hz, gain_db
    frequencySelected = Signal(float, float)  # freq_hz, gain_db

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setMinimumHeight(160)
        self.setMouseTracking(True)

        self._hover_x = None
        self._hover_y = None

        self._padding_left = 30
        self._padding_right = 30
        self._padding_top = 10
        self._padding_bottom = 18

        self._gain_db_min = -15.0
        self._gain_db_max = 15.0

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.fillRect(self.rect(), QColor("#1E1E22"))

        inner_rect = self._inner_rect()
        painter.fillRect(inner_rect, QColor("#18181D"))

        if self._hover_x is not None and self._hover_y is not None:
            pen = QPen(QColor("#78A6FF"))
            pen.setWidth(2)
            painter.setPen(pen)

            x = int(self._hover_x)
            y = int(self._hover_y)

            x = max(inner_rect.left(), min(inner_rect.right(), x))
            y = max(inner_rect.top(), min(inner_rect.bottom(), y))

            # вертикаль (частота)
            painter.drawLine(x, inner_rect.top(), x, inner_rect.bottom())
            # горизонталь (gain)
            painter.drawLine(inner_rect.left(), y, inner_rect.right(), y)

        painter.end()

    def mouseMoveEvent(self, event):
        x = event.position().x()
        y = event.position().y()
        self._hover_x = x
        self._hover_y = y

        freq = self._x_to_freq(x)
        gain_db = self._y_to_gain_db(y)

        self.frequencyHovered.emit(freq, gain_db)
        self.update()

    def mousePressEvent(self, event):
        if event.button() == Qt.LeftButton:
            x = event.position().x()
            y = event.position().y()
            freq = self._x_to_freq(x)
            gain_db = self._y_to_gain_db(y)
            self.frequencySelected.emit(freq, gain_db)

    def _inner_rect(self):
        w = max(0, self.width() - self._padding_left - self._padding_right)
        h = max(0, self.height() - self._padding_top - self._padding_bottom)
        return self.rect().adjusted(
            self._padding_left,
            self._padding_top,
            -self._padding_right,
            -self._padding_bottom,
        )

    def _x_to_freq(self, x: float) -> float:
        inner = self._inner_rect()
        if inner.width() <= 0:
            return 20.0

        pos = (x - inner.left()) / inner.width()
        pos = max(0.0, min(1.0, pos))

        f_min, f_max = 20.0, 20000.0
        log_min, log_max = log10(f_min), log10(f_max)
        log_f = log_min + pos * (log_max - log_min)
        return 10 ** log_f

    def _y_to_gain_db(self, y: float) -> float:
        inner = self._inner_rect()
        if inner.height() <= 0:
            return 0.0

        # pos=0 наверху, pos=1 внизу
        pos = (y - inner.top()) / inner.height()
        pos = max(0.0, min(1.0, pos))

        # наверху +15 dB, внизу -15 dB
        g_min = self._gain_db_min
        g_max = self._gain_db_max
        gain_db = g_max + (g_min - g_max) * pos
        return gain_db
