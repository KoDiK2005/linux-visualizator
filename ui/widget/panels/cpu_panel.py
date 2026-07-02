"""Кольцевые индикаторы загрузки по каждому ядру CPU."""

from PySide6.QtCore import QRectF, QSize, Qt
from PySide6.QtGui import QColor, QFont, QPainter, QPen
from PySide6.QtWidgets import QWidget

from core.models import CpuSnapshot
from ui.widget import theme

RING_SIZE = 34
RING_SPACING = 6
RING_THICKNESS = 4


class CpuPanel(QWidget):
    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self._per_core_percent: list[float] = []
        self.setMinimumHeight(RING_SIZE + 8)

    def update_snapshot(self, cpu: CpuSnapshot) -> None:
        self._per_core_percent = cpu.per_core_percent
        self.updateGeometry()
        self.update()

    def sizeHint(self) -> QSize:
        count = max(len(self._per_core_percent), 1)
        width = count * (RING_SIZE + RING_SPACING) + RING_SPACING
        return QSize(width, RING_SIZE + 8)

    def paintEvent(self, event) -> None:  # noqa: N802 (Qt override)
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)
        painter.setFont(QFont(theme.FONT_FAMILY, 7))

        x = RING_SPACING
        for percent in self._per_core_percent:
            rect = QRectF(x, 4, RING_SIZE, RING_SIZE)

            bg_pen = QPen(QColor(255, 255, 255, 40), RING_THICKNESS)
            bg_pen.setCapStyle(Qt.RoundCap)
            painter.setPen(bg_pen)
            painter.drawArc(rect, 0, 360 * 16)

            fg_pen = QPen(QColor(theme.ACCENT_CPU), RING_THICKNESS)
            fg_pen.setCapStyle(Qt.RoundCap)
            painter.setPen(fg_pen)
            span = int(-percent / 100 * 360 * 16)
            painter.drawArc(rect, 90 * 16, span)

            painter.setPen(QColor(theme.TEXT_COLOR))
            painter.drawText(rect, Qt.AlignCenter, f"{int(percent)}")

            x += RING_SIZE + RING_SPACING
