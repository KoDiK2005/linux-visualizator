"""Переиспользуемый двухрядный спарклайн (например, приём/отправка или чтение/запись)."""

from collections import deque

from PySide6.QtCore import QRectF, Qt
from PySide6.QtGui import QColor, QFont, QPainter, QPainterPath, QPen
from PySide6.QtWidgets import QWidget

from ui.widget import theme

HISTORY_LEN = 60
PANEL_HEIGHT = 40
LABEL_HEIGHT = 14


class SparklinePanel(QWidget):
    """Базовая панель: две линии со своей историей значений и подписью текущих чисел."""

    def __init__(
        self,
        color_a: str,
        color_b: str,
        symbol_a: str,
        symbol_b: str,
        parent: QWidget | None = None,
    ) -> None:
        super().__init__(parent)
        self._color_a = color_a
        self._color_b = color_b
        self._symbol_a = symbol_a
        self._symbol_b = symbol_b
        self._history_a: deque[float] = deque(maxlen=HISTORY_LEN)
        self._history_b: deque[float] = deque(maxlen=HISTORY_LEN)
        self._unit_mode = "bytes"
        self._scale = 1.0
        self.setMinimumHeight(PANEL_HEIGHT)

    def set_unit_mode(self, unit_mode: str) -> None:
        """unit_mode: "bytes" (KB/s) или "bits" (Kb/s)."""
        self._unit_mode = unit_mode
        self.update()

    def set_scale(self, scale: float) -> None:
        self._scale = scale
        self.setMinimumHeight(round(PANEL_HEIGHT * scale))
        self.updateGeometry()
        self.update()

    def update_values(self, value_a: float, value_b: float) -> None:
        self._history_a.append(value_a)
        self._history_b.append(value_b)
        self.update()

    def _format_rate(self, bytes_per_sec: float) -> str:
        if self._unit_mode == "bits":
            return f"{bytes_per_sec * 8 / 1024:5.1f} Kb/s"
        return f"{bytes_per_sec / 1024:5.1f} KB/s"

    def paintEvent(self, event) -> None:  # noqa: N802 (Qt override)
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)
        width = self.width()
        height = self.height()
        label_height = LABEL_HEIGHT * self._scale

        max_value = max([*self._history_a, *self._history_b, 1.0])

        self._draw_line(painter, self._history_a, max_value, width, height, label_height, self._color_a)
        self._draw_line(painter, self._history_b, max_value, width, height, label_height, self._color_b)

        current_a = self._history_a[-1] if self._history_a else 0.0
        current_b = self._history_b[-1] if self._history_b else 0.0
        painter.setPen(QColor(theme.TEXT_COLOR))
        painter.setFont(QFont(theme.FONT_FAMILY, round(7 * self._scale)))
        painter.drawText(
            QRectF(0, 0, width, label_height),
            Qt.AlignLeft,
            f"{self._symbol_a}{self._format_rate(current_a)}  "
            f"{self._symbol_b}{self._format_rate(current_b)}",
        )

    def _draw_line(
        self,
        painter: QPainter,
        history: deque[float],
        max_value: float,
        width: float,
        height: float,
        label_height: float,
        color: str,
    ) -> None:
        if len(history) < 2:
            return
        step = width / (HISTORY_LEN - 1)
        offset = HISTORY_LEN - len(history)
        plot_top = label_height
        plot_height = height - plot_top - 2

        path = QPainterPath()
        for idx, value in enumerate(history):
            x = (offset + idx) * step
            y = plot_top + plot_height - (value / max_value) * plot_height
            if idx == 0:
                path.moveTo(x, y)
            else:
                path.lineTo(x, y)

        painter.setPen(QPen(QColor(color), 1.5))
        painter.drawPath(path)
