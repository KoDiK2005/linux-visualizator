"""Кольцевые индикаторы загрузки по каждому ядру CPU."""

from PySide6.QtCore import QRectF, QSize, Qt
from PySide6.QtGui import QColor, QFont, QPainter, QPen
from PySide6.QtWidgets import QWidget

from core.models import CpuSnapshot
from ui.widget import theme
from ui.widget.animation import SmoothedList
from ui.widget.severity import severity_color

RING_SIZE = 34
RING_SPACING = 6
RING_THICKNESS = 4
STATS_HEIGHT = 12


class CpuPanel(QWidget):
    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self._smoothed = SmoothedList()
        self._total_percent = 0.0
        self._frequency_mhz: float | None = None
        self._temperature_c: float | None = None
        self.setMinimumHeight(STATS_HEIGHT + RING_SIZE + 8)

    def update_snapshot(self, cpu: CpuSnapshot) -> None:
        self._smoothed.set_targets(cpu.per_core_percent)
        self._total_percent = cpu.total_percent
        self._frequency_mhz = cpu.frequency_mhz
        self._temperature_c = cpu.temperature_c
        self.updateGeometry()

    def animate(self) -> bool:
        changed = self._smoothed.step()
        if changed:
            self.update()
        return changed

    def sizeHint(self) -> QSize:
        count = max(len(self._smoothed.values), 1)
        width = count * (RING_SIZE + RING_SPACING) + RING_SPACING
        return QSize(width, STATS_HEIGHT + RING_SIZE + 8)

    def paintEvent(self, event) -> None:  # noqa: N802 (Qt override)
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)

        painter.setPen(QColor(theme.TEXT_COLOR))
        painter.setFont(QFont(theme.FONT_FAMILY, 7))
        painter.drawText(
            QRectF(0, 0, self.width(), STATS_HEIGHT), Qt.AlignLeft | Qt.AlignVCenter,
            self._stats_text(),
        )

        painter.setFont(QFont(theme.FONT_FAMILY, 7))
        x = RING_SPACING
        for percent in self._smoothed.values:
            rect = QRectF(x, STATS_HEIGHT + 4, RING_SIZE, RING_SIZE)

            bg_pen = QPen(QColor(255, 255, 255, 40), RING_THICKNESS)
            bg_pen.setCapStyle(Qt.RoundCap)
            painter.setPen(bg_pen)
            painter.drawArc(rect, 0, 360 * 16)

            fg_pen = QPen(severity_color(theme.ACCENT_CPU, percent), RING_THICKNESS)
            fg_pen.setCapStyle(Qt.RoundCap)
            painter.setPen(fg_pen)
            span = int(-percent / 100 * 360 * 16)
            painter.drawArc(rect, 90 * 16, span)

            painter.setPen(QColor(theme.TEXT_COLOR))
            painter.drawText(rect, Qt.AlignCenter, f"{int(percent)}")

            x += RING_SIZE + RING_SPACING

    def _stats_text(self) -> str:
        parts = [f"{self._total_percent:.0f}%"]
        if self._frequency_mhz:
            parts.append(f"{self._frequency_mhz / 1000:.1f} GHz")
        if self._temperature_c is not None:
            parts.append(f"{self._temperature_c:.0f}°C")
        return "  ".join(parts)
